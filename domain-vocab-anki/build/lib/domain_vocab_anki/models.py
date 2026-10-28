"""Validated data shared by lesson generation and Anki sync."""

from dataclasses import asdict, dataclass
import re


WORD_FIELDS = (
    "term", "ipa", "part_of_speech", "meaning_zh", "context_zh",
    "example_en", "example_zh", "collocation_zh",
)


def key_for(term: str) -> str:
    """Normalize whitespace and case for duplicate detection."""
    return re.sub(r"\s+", " ", term.strip()).casefold()


@dataclass(frozen=True)
class Word:
    term: str
    ipa: str
    part_of_speech: str
    meaning_zh: str
    context_zh: str
    example_en: str
    example_zh: str
    collocation_zh: str

    @classmethod
    def from_dict(cls, data: dict) -> "Word":
        if not isinstance(data, dict):
            raise ValueError("Each word must be an object")
        values = {field: data.get(field) for field in WORD_FIELDS}
        if any(not isinstance(value, str) or not value.strip() for value in values.values()):
            raise ValueError(f"Word has missing fields: {data.get('term', '<unknown>')}")
        word = cls(**{field: value.strip() for field, value in values.items()})
        if key_for(word.term) not in word.example_en.casefold():
            raise ValueError(f"Example must use its term: {word.term}")
        return word

    def as_dict(self) -> dict:
        return asdict(self)
