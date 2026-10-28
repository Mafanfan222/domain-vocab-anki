"""SQLite learning record and deterministic spaced-review queue."""

from datetime import date, timedelta
import json
from pathlib import Path
import sqlite3

from .models import Word, key_for


class Store:
    def __init__(self, path: str | Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS terms (
              term_key TEXT PRIMARY KEY,
              first_date TEXT NOT NULL,
              anchor_date TEXT NOT NULL,
              previous_anchor TEXT,
              status TEXT NOT NULL DEFAULT 'unassessed',
              correct_streak INTEGER NOT NULL DEFAULT 0,
              word_json TEXT NOT NULL,
              anki_synced INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS review_seen (
              term_key TEXT NOT NULL,
              anchor_date TEXT NOT NULL,
              interval_day INTEGER NOT NULL,
              asked_date TEXT NOT NULL,
              grade TEXT,
              PRIMARY KEY (term_key, anchor_date, interval_day),
              FOREIGN KEY (term_key) REFERENCES terms(term_key)
            );
            CREATE TABLE IF NOT EXISTS lessons (
              lesson_date TEXT PRIMARY KEY,
              profile_name TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              markdown TEXT NOT NULL
            );
            """
        )

    def close(self) -> None:
        self.db.close()

    def existing_keys(self) -> set[str]:
        return {row[0] for row in self.db.execute("SELECT term_key FROM terms")}

    def get_lesson(self, day: date) -> tuple[dict, str] | None:
        row = self.db.execute(
            "SELECT payload_json, markdown FROM lessons WHERE lesson_date=?", (day.isoformat(),)
        ).fetchone()
        return (json.loads(row[0]), row[1]) if row else None

    def due_reviews(self, day: date, intervals: list[int], per_batch: int, maximum: int) -> list[dict]:
        seen = {
            (row[0], row[1], row[2])
            for row in self.db.execute("SELECT term_key, anchor_date, interval_day FROM review_seen")
        }
        groups: dict[tuple[str, str, int], list[dict]] = {}
        for row in self.db.execute("SELECT * FROM terms"):
            anchor = date.fromisoformat(row["anchor_date"])
            for interval in intervals:
                due = anchor + timedelta(days=interval)
                if due > day or (row["term_key"], row["anchor_date"], interval) in seen:
                    continue
                group = (due.isoformat(), row["anchor_date"], interval)
                groups.setdefault(group, []).append(
                    {
                        "term_key": row["term_key"],
                        "anchor_date": row["anchor_date"],
                        "interval_day": interval,
                        "due_date": due.isoformat(),
                        "status": row["status"],
                        "word": json.loads(row["word_json"]),
                    }
                )
        priority = {"reinforce": 0, "unassessed": 1, "normal": 2}
        selected: list[dict] = []
        for group in sorted(groups):
            candidates = sorted(groups[group], key=lambda item: (priority.get(item["status"], 1), item["term_key"]))
            selected.extend(candidates[: min(per_batch, maximum - len(selected))])
            if len(selected) >= maximum:
                break
        return selected

    def save_lesson(self, day: date, profile_name: str, payload: dict, markdown: str) -> None:
        words = [Word.from_dict(item) for item in payload["words"]]
        with self.db:
            self.db.execute(
                "INSERT INTO lessons(lesson_date, profile_name, payload_json, markdown) VALUES(?,?,?,?)",
                (day.isoformat(), profile_name, json.dumps(payload, ensure_ascii=False), markdown),
            )
            for word in words:
                self.db.execute(
                    "INSERT INTO terms(term_key, first_date, anchor_date, word_json) VALUES(?,?,?,?)",
                    (key_for(word.term), day.isoformat(), day.isoformat(), json.dumps(word.as_dict(), ensure_ascii=False)),
                )
            for item in payload["reviews"]:
                self.db.execute(
                    "INSERT INTO review_seen(term_key, anchor_date, interval_day, asked_date) VALUES(?,?,?,?)",
                    (item["term_key"], item["anchor_date"], item["interval_day"], day.isoformat()),
                )

    def pending_anki(self) -> list[dict]:
        return [
            {"term_key": row["term_key"], "first_date": row["first_date"], "word": json.loads(row["word_json"])}
            for row in self.db.execute("SELECT term_key, first_date, word_json FROM terms WHERE anki_synced=0 ORDER BY first_date, term_key")
        ]

    def mark_anki_synced(self, keys: list[str]) -> None:
        with self.db:
            self.db.executemany("UPDATE terms SET anki_synced=1 WHERE term_key=?", [(key,) for key in keys])

    def grade(self, term: str, correct: bool, day: date) -> None:
        key = key_for(term)
        row = self.db.execute("SELECT * FROM terms WHERE term_key=?", (key,)).fetchone()
        if not row:
            raise ValueError(f"Unknown term: {term}")
        review = self.db.execute(
            "SELECT anchor_date, interval_day FROM review_seen WHERE term_key=? AND grade IS NULL "
            "AND asked_date<=? ORDER BY asked_date DESC, interval_day DESC LIMIT 1",
            (key, day.isoformat()),
        ).fetchone()
        if not review:
            raise ValueError(f"No unanswered review question for: {term}")
        with self.db:
            self.db.execute(
                "UPDATE review_seen SET grade=? WHERE term_key=? AND anchor_date=? AND interval_day=?",
                ("correct" if correct else "incorrect", key, review["anchor_date"], review["interval_day"]),
            )
            if not correct:
                previous = row["previous_anchor"] or row["anchor_date"]
                self.db.execute(
                    "UPDATE terms SET anchor_date=?, previous_anchor=?, status='reinforce', correct_streak=0 WHERE term_key=?",
                    (day.isoformat(), previous, key),
                )
            elif row["status"] == "reinforce":
                streak = row["correct_streak"] + 1
                if streak >= 2:
                    self.db.execute(
                        "UPDATE terms SET anchor_date=?, previous_anchor=NULL, status='normal', correct_streak=0 WHERE term_key=?",
                        (row["previous_anchor"], key),
                    )
                else:
                    self.db.execute("UPDATE terms SET correct_streak=? WHERE term_key=?", (streak, key))
            else:
                self.db.execute("UPDATE terms SET status='normal' WHERE term_key=?", (key,))
