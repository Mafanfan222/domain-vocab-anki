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
    dialogue = content["dialogue_en"].strip()
    count = len(re.findall(r"\b[\w'-]+\b", dialogue))
    if not 80 <= count <= 120:
        raise ValueError(f"Customer dialogue must be 80–120 English words; got {count}")
    if sum(bool(re.search(r"(?<!\w)" + re.escape(word.term) + r"(?!\w)", dialogue, re.I)) for word in words) < min(6, len(words)):
        raise ValueError("Customer dialogue must naturally use at least six new terms")
    for field in ("dialogue_zh", "speaking_task_zh"):
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
            "dialogue_en": profile.dialogue_en,
            "dialogue_zh": profile.dialogue_zh,
            "speaking_task_zh": profile.speaking_task_zh,
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
            "dialogue_en": {"type": "string"},
            "dialogue_zh": {"type": "string"},
            "speaking_task_zh": {"type": "string"},
        },
        "required": ["words", "dialogue_en", "dialogue_zh", "speaking_task_zh"],
        "additionalProperties": False,
    }
    instructions = (
        "Create a practical bilingual business English lesson. Return exactly the requested number of distinct terms. "
        "Each example_en must contain its exact term. Dialogue must be 80–120 English words and naturally use at least "
        "six of today's terms. Never invent a company's customers, certifications, specifications or sales countries."
    )
    request = {
        "domain_context": profile.domain_context,
        "customer_scenario": profile.customer_scenario,
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
