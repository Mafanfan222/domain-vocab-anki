"""Local AnkiConnect bridge with explicit Front/Back mapping."""

from html import escape
import json
from urllib.request import Request, urlopen

from .models import Word, key_for


def card_back(word: Word, first_date: str) -> str:
    """Keep all study content on the reverse side of a Basic note."""
    rows = (
        ("音标", word.ipa), ("词性", word.part_of_speech), ("中文释义", word.meaning_zh),
        ("使用场景", word.context_zh), ("English example", word.example_en),
        ("中文例句", word.example_zh), ("搭配/易错", word.collocation_zh),
        ("首次学习", first_date),
    )
    return "".join(f"<p><b>{escape(label)}：</b>{escape(value)}</p>" for label, value in rows)


class AnkiConnect:
    def __init__(self, url: str, timeout: int = 8):
        self.url = url
        self.timeout = timeout

    def call(self, action: str, **params):
        body = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
        request = Request(self.url, data=body, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            result = json.load(response)
        if result.get("error"):
            raise RuntimeError(f"AnkiConnect {action}: {result['error']}")
        return result["result"]


def sync_pending(store, settings: dict, client: AnkiConnect | None = None) -> int:
    pending = store.pending_anki()
    if not pending:
        return 0
    client = client or AnkiConnect(settings["url"])
    deck = settings["deck"]
    note_type = settings["note_type"]
    front = settings["front_field"]
    back = settings["back_field"]
    fields = client.call("modelFieldNames", modelName=note_type)
    if front not in fields or back not in fields:
        raise ValueError(f"Note type {note_type!r} must contain {front!r} and {back!r}")
    client.call("createDeck", deck=deck)
    ids = client.call("findNotes", query=f'deck:"{deck}"')
    existing: dict[str, dict] = {}
    for start in range(0, len(ids), 100):
        for note in client.call("notesInfo", notes=ids[start:start + 100]):
            value = note.get("fields", {}).get(front, {}).get("value", "")
            existing[key_for(value)] = note
    synced = []
    for item in pending:
        word = Word.from_dict(item["word"])
        key = key_for(word.term)
        reverse = card_back(word, item["first_date"])
        if key in existing:
            note = existing[key]
            if not note["fields"].get(back, {}).get("value", "").strip():
                client.call("updateNoteFields", note={"id": note["noteId"], "fields": {back: reverse}})
        else:
            client.call("addNote", note={
                "deckName": deck,
                "modelName": note_type,
                "fields": {front: escape(word.term), back: reverse},
                "options": {"allowDuplicate": False},
                "tags": ["domain-vocab-anki"],
            })
        synced.append(key)
        # Commit each successful item so a later connection failure can be retried safely.
        store.mark_anki_synced([key])
    return len(synced)
