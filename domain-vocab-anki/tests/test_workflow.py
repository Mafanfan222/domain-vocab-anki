import json
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from domain_vocab_anki.anki import card_back, sync_pending
from domain_vocab_anki.cli import main
from domain_vocab_anki.config import load_profile
from domain_vocab_anki.models import Word
from domain_vocab_anki.store import Store


ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / "examples" / "wind-gearbox.json"


class FakeAnki:
    def __init__(self):
        self.notes = []

    def call(self, action, **params):
        if action == "modelFieldNames":
            return ["Front", "Back"]
        if action == "createDeck":
            return 1
        if action == "findNotes":
            return list(range(len(self.notes)))
        if action == "notesInfo":
            return [self.notes[i] for i in params["notes"]]
        if action == "addNote":
            fields = params["note"]["fields"]
            self.notes.append({"noteId": len(self.notes), "fields": {name: {"value": value} for name, value in fields.items()}})
            return len(self.notes)
        if action == "updateNoteFields":
            note = self.notes[params["note"]["id"]]
            for name, value in params["note"]["fields"].items():
                note["fields"][name] = {"value": value}
            return None
        raise AssertionError(action)


class WorkflowTests(unittest.TestCase):
    def test_daily_run_is_idempotent_and_review_is_ungraded(self):
        with TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "learning.sqlite3")
            output = str(Path(tmp) / "lessons")
            args = ["run", "--config", str(PROFILE), "--state", state, "--output", output, "--date", "2026-10-28", "--no-anki"]
            self.assertEqual(main(args), 0)
            first = Path(output, "2026-10-28.md").read_text(encoding="utf-8")
            self.assertIn("gearbox housing", first)
            self.assertIn("今日为第一课", first)
            self.assertEqual(main(args), 0)
            store = Store(state)
            self.assertEqual(len(store.existing_keys()), 10)
            next_day = date(2026, 10, 29)
            due = store.due_reviews(next_day, [1, 2, 4, 7, 15, 30], 2, 12)
            self.assertEqual(len(due), 2)
            self.assertTrue(all(item["interval_day"] == 1 for item in due))
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM review_seen WHERE grade IS NOT NULL").fetchone()[0], 0)
            store.close()

    def test_wrong_answer_resets_schedule_and_correct_answers_restore(self):
        with TemporaryDirectory() as tmp:
            state = str(Path(tmp) / "learning.sqlite3")
            profile = load_profile(PROFILE)
            payload = {
                "words": profile.bank,
                "reviews": [],
                "dialogue_en": profile.dialogue_en,
                "dialogue_zh": profile.dialogue_zh,
                "speaking_task_zh": profile.speaking_task_zh,
            }
            store = Store(state)
            start = date(2026, 10, 28)
            store.save_lesson(start, profile.name, payload, "demo")
            day1 = start + timedelta(days=1)
            due = store.due_reviews(day1, [1, 2, 4, 7, 15, 30], 2, 12)
            payload["words"] = []
            payload["reviews"] = due
            store.save_lesson(day1, profile.name, payload, "review")
            term = due[0]["word"]["term"]
            store.grade(term, False, day1)
            status = store.db.execute("SELECT status FROM terms WHERE term_key=?", (term.casefold(),)).fetchone()[0]
            self.assertEqual(status, "reinforce")
            for offset in (1, 2):
                day = day1 + timedelta(days=offset)
                due = store.due_reviews(day, [1, 2, 4, 7, 15, 30], 2, 12)
                match = next(item for item in due if item["term_key"] == term.casefold() and item["anchor_date"] == day1.isoformat())
                payload["reviews"] = [match]
                store.save_lesson(day, profile.name, payload, "review")
                store.grade(term, True, day)
            status = store.db.execute("SELECT status, anchor_date FROM terms WHERE term_key=?", (term.casefold(),)).fetchone()
            self.assertEqual(tuple(status), ("normal", start.isoformat()))
            store.close()

    def test_anki_back_has_all_details_and_sync_deduplicates(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "state.sqlite3")
            profile = load_profile(PROFILE)
            payload = {
                "words": profile.bank,
                "reviews": [],
                "dialogue_en": profile.dialogue_en,
                "dialogue_zh": profile.dialogue_zh,
                "speaking_task_zh": profile.speaking_task_zh,
            }
            store.save_lesson(date(2026, 10, 28), profile.name, payload, "demo")
            client = FakeAnki()
            self.assertEqual(sync_pending(store, profile.anki, client), 10)
            self.assertEqual(sync_pending(store, profile.anki, client), 0)
            self.assertEqual(len(client.notes), 10)
            back = client.notes[0]["fields"]["Back"]["value"]
            self.assertIn("音标", back)
            self.assertIn("中文释义", back)
            self.assertIn("使用场景", back)
            self.assertIn("English example", back)
            self.assertIn("中文例句", back)
            self.assertNotIn("中文释义", client.notes[0]["fields"]["Front"]["value"])
            store.close()


if __name__ == "__main__":
    unittest.main()
