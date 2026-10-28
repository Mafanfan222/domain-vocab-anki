"""Command line entry point for local daily runs and answer grading."""

import argparse
from datetime import date
from pathlib import Path
import sqlite3
import sys

from .anki import sync_pending
from .config import load_profile
from .lesson import render
from .providers import generate
from .store import Store


def _date(value: str) -> date:
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="domain-vocab-anki")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Generate or retrieve today's lesson, then sync cards")
    run.add_argument("--config", required=True)
    run.add_argument("--state", default="state/learning.sqlite3")
    run.add_argument("--output", default="lessons")
    run.add_argument("--date", type=_date, default=None)
    run.add_argument("--no-anki", action="store_true")
    sync = sub.add_parser("sync", help="Retry unsynced cards")
    sync.add_argument("--config", required=True)
    sync.add_argument("--state", default="state/learning.sqlite3")
    grade = sub.add_parser("grade", help="Record a real answer to an asked review question")
    grade.add_argument("--state", default="state/learning.sqlite3")
    grade.add_argument("--term", required=True)
    group = grade.add_mutually_exclusive_group(required=True)
    group.add_argument("--correct", action="store_true")
    group.add_argument("--incorrect", action="store_true")
    grade.add_argument("--date", type=_date, default=None)
    status = sub.add_parser("status", help="Show first-study dates, attempts and mastery state")
    status.add_argument("--state", default="state/learning.sqlite3")
    args = parser.parse_args(argv)
    store = Store(args.state)
    try:
        if args.command == "grade":
            store.grade(args.term, args.correct, args.date or date.today())
            print(f"Recorded {args.term}: {'correct' if args.correct else 'incorrect'}")
            return 0
        if args.command == "status":
            for item in store.term_status():
                print(f"{item['term_key']} | first={item['first_date']} | reviews={item['review_count']} "
                      f"| correct={item['correct_count']} | incorrect={item['incorrect_count']} "
                      f"| status={item['status']} | anki={'synced' if item['anki_synced'] else 'queued'}")
            return 0
        profile = load_profile(args.config)
        if args.command == "run":
            day = args.date or date.today()
            existing = store.get_lesson(day)
            if existing:
                markdown = existing[1]
                print(f"Reusing existing lesson for {day.isoformat()}")
            else:
                known = store.existing_keys()
                reviews = store.due_reviews(day, profile.review_intervals, profile.review_per_batch, profile.max_review_questions)
                payload = generate(profile, known)
                payload["reviews"] = reviews
                payload["has_history"] = bool(known)
                markdown = render(day, profile, payload)
                store.save_lesson(day, profile.name, payload, markdown)
            output = Path(args.output) / f"{day.isoformat()}.md"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(markdown, encoding="utf-8")
            print(f"Lesson: {output.resolve()}")
            if args.no_anki:
                print("Anki sync skipped; pending cards remain queued")
                return 0
        try:
            count = sync_pending(store, profile.anki)
            print(f"Anki cards synchronized: {count}")
        except (OSError, RuntimeError) as exc:
            print(f"Anki unavailable; cards remain queued. Run sync when Anki is open. ({exc})", file=sys.stderr)
        return 0
    except (ValueError, KeyError, sqlite3.Error) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    raise SystemExit(main())
