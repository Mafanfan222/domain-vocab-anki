"""Lesson content providers. The bank works offline; AI is opt in."""

import json
import os
import re

from .config import Profile
from .models import Word, key_for


def _validate(profile: Profile, content: dict, existing: set[str]) -> dict:
    words = [Word.from_dict(item) for item in content["words"]]
    keys = [key_for(word.term) for word in words]
    if len(words) != profile.daily_new or len(set(keys)) != len(keys):
        raise ValueError(f"Expected exactly {profile.daily_new} distinct new terms")
    if set(keys) & existing:
        raise ValueError("Provider returned previously learned terms")
    sample = content["sample_en"].strip()
    count = len(re.findall(r"\b[\w'-]+\b", sample))
    if not 80 <= count <= 120:
        raise ValueError(f"English sample must be 80–120 words; got {count}")
    if sum(bool(re.search(r"(?<!\w)" + re.escape(word.term) + r"(?!\w)", sample, re.I)) for word in words) < min(6, len(words)):
        raise ValueError("English sample must naturally use at least six new terms")
    for field in ("sample_zh", "practice_task_zh"):
        if not isinstance(content.get(field), str) or not content[field].strip():
            raise ValueError(f"Missing {field}")
    return {**content, "words": [word.as_dict() for word in words]}


def generate(profile: Profile, existing: set[str]) -> dict:
    if profile.provider == "bank":
        available = [item for item in profile.bank if key_for(item.get("term", "")) not in existing]
        if len(available) < profile.daily_new:
            raise ValueError("Word bank exhausted. Add terms or switch provider to openai")
        content = {
            "words": available[:profile.daily_new],
            "sample_en": profile.sample_en,
            "sample_zh": profile.sample_zh,
            "practice_task_zh": profile.practice_task_zh,
        }
        return _validate(profile, content, existing)
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError("Set OPENAI_API_KEY in your environment for the openai provider")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the optional AI dependency: pip install '.[ai]'") from exc
    word_fields = {
        field: {"type": "string"}
        for field in ("term", "ipa", "part_of_speech", "meaning_zh", "context_zh", "example_en", "example_zh", "collocation_zh")
    }
    schema = {
        "type": "object",
        "properties": {
            "words": {"type": "array", "items": {"type": "object", "properties": word_fields, "required": list(word_fields), "additionalProperties": False}},
            "sample_en": {"type": "string"},
            "sample_zh": {"type": "string"},
            "practice_task_zh": {"type": "string"},
        },
        "required": ["words", "sample_en", "sample_zh", "practice_task_zh"],
        "additionalProperties": False,
    }
    instructions = (
        "Create a practical bilingual Chinese-English vocabulary lesson for the specified learning domain and goal. "
        "The domain may be scientific, technical, cultural, everyday, academic or professional; do not assume a sales context. "
        "Return exactly the requested number of distinct terms. Each example_en must contain its exact term. "
        "Write an 80–120-word English sample in the requested format, naturally using at least six new terms, "
        "with an accurate Chinese translation. Give one short application task suitable for the learning goal. "
        "Avoid unsupported factual claims, invented figures and invented affiliations."
    )
    request = {
        "domain_context": profile.domain_context,
        "learning_goal": profile.learning_goal,
        "use_scenario": profile.use_scenario,
        "sample_format": profile.sample_format,
        "learner_level": profile.learner_level,
        "topics": profile.topics,
        "prohibited_claims": profile.prohibited_claims,
        "daily_new": profile.daily_new,
        "existing_terms": sorted(existing),
    }
    client = OpenAI()
    for _ in range(2):
        response = client.responses.create(
            model=profile.model,
            instructions=instructions,
            input=json.dumps(request, ensure_ascii=False),
            text={"format": {"type": "json_schema", "name": "domain_lesson", "strict": True, "schema": schema}},
        )
        try:
            return _validate(profile, json.loads(response.output_text), existing)
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            request["correction"] = str(exc)
    raise ValueError("AI provider did not produce a valid lesson after two attempts")
