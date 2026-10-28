"""User-editable domain profile loader."""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Profile:
    name: str
    domain_context: str
    customer_scenario: str
    learner_level: str
    topics: list[str]
    prohibited_claims: str
    provider: str
    model: str
    daily_new: int
    review_intervals: list[int]
    review_per_batch: int
    max_review_questions: int
    bank: list[dict]
    dialogue_en: str
    dialogue_zh: str
    speaking_task_zh: str
    anki: dict


def load_profile(path: str | Path) -> Profile:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = (
        "name", "domain_context", "customer_scenario", "learner_level",
        "topics", "provider", "daily_new", "anki",
    )
    if any(key not in data for key in required):
        raise ValueError(f"Profile must contain: {', '.join(required)}")
    provider = data["provider"]
    if provider not in ("bank", "openai"):
        raise ValueError("provider must be 'bank' or 'openai'")
    if provider == "openai" and not data.get("model"):
        raise ValueError("Set model for the OpenAI provider")
    if not isinstance(data["topics"], list) or not data["topics"]:
        raise ValueError("topics must be a nonempty list")
    daily_new = data["daily_new"]
    if not isinstance(daily_new, int) or daily_new < 1:
        raise ValueError("daily_new must be a positive integer")
    intervals = data.get("review_intervals", [1, 2, 4, 7, 15, 30])
    if not isinstance(intervals, list) or not intervals or any(not isinstance(n, int) or n < 1 for n in intervals):
        raise ValueError("review_intervals must contain positive integers")
    if intervals != sorted(set(intervals)):
        raise ValueError("review_intervals must be sorted and unique")
    per_batch = data.get("review_per_batch", 2)
    max_questions = data.get("max_review_questions", 12)
    if not isinstance(per_batch, int) or per_batch < 1 or not isinstance(max_questions, int) or max_questions < 1:
        raise ValueError("Review limits must be positive integers")
    anki = data["anki"]
    if not isinstance(anki, dict) or any(not anki.get(key) for key in ("url", "deck", "note_type", "front_field", "back_field")):
        raise ValueError("anki requires url, deck, note_type, front_field and back_field")
    return Profile(
        name=str(data["name"]),
        domain_context=str(data["domain_context"]),
        customer_scenario=str(data["customer_scenario"]),
        learner_level=str(data["learner_level"]),
        topics=[str(topic) for topic in data["topics"]],
        prohibited_claims=str(data.get("prohibited_claims", "")),
        provider=provider,
        model=str(data.get("model", "")),
        daily_new=daily_new,
        review_intervals=intervals,
        review_per_batch=per_batch,
        max_review_questions=max_questions,
        bank=data.get("bank", []),
        dialogue_en=str(data.get("dialogue_en", "")),
        dialogue_zh=str(data.get("dialogue_zh", "")),
        speaking_task_zh=str(data.get("speaking_task_zh", "")),
        anki=anki,
    )
