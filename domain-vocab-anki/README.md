# Domain Vocab → Anki

可配置领域的每日双语商务英语词汇课：每天生成新词、按 D+1/2/4/7/15/30 复习，并将完整卡片同步到本机 Anki。领域、客户场景、主题和禁用的未经核实说法都由 JSON 配置决定。项目附带风电齿轮箱离线演示，也可改成 SaaS、医疗器械、机械制造等领域。

**A configurable daily bilingual vocabulary lesson for a chosen professional domain, with spaced review and local AnkiConnect sync.** Python 3.11+; no account or cloud service is required for the offline word-bank demo. Continuous AI-generated lessons require an OpenAI API key.

## 1. 安装 / Install

```powershell
git clone https://github.com/Mafanfan222/domain-vocab-anki.git
cd domain-vocab-anki
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

macOS/Linux: activate with `source .venv/bin/activate`. For AI generation, install `python -m pip install -e '.[ai]'` and set `OPENAI_API_KEY` in the local environment. Never put the key in a profile or commit it.

## 2. 选择领域 / Choose a domain

Copy `examples/custom-domain.json` to a private local path and edit:

| Field | Purpose |
| --- | --- |
| `name`, `domain_context`, `customer_scenario` | Lesson title, subject matter, and customer situation |
| `learner_level`, `topics` | Difficulty and rotating themes |
| `prohibited_claims` | Claims the generator must avoid without evidence |
| `provider` | `bank` for an offline fixed word list, `openai` for ongoing generation |
| `daily_new` | Number of new words; default examples use 10 |
| `review_intervals` | Days after first study or a reset: `[1,2,4,7,15,30]` |
| `anki` | Local AnkiConnect URL, deck, note type, Front and Back field names |

The offline [`wind-gearbox.json`](examples/wind-gearbox.json) contains **one demonstration day** of ten public example terms. Add more words and a matching 80–120-word dialogue to extend bank mode. For an ongoing daily course, use the AI profile with your own domain. Each new term has phonetics, Chinese meaning, use context, bilingual example, and a collocation or common error.

## 3. 运行 / Run

```powershell
domain-vocab-anki run --config examples/wind-gearbox.json --no-anki
domain-vocab-anki run --config examples/custom-domain.json
domain-vocab-anki sync --config examples/custom-domain.json
```

The lesson is saved as `lessons/YYYY-MM-DD.md`; learning history is stored in `state/learning.sqlite3`. Running again on the same date reuses that lesson and retries any pending cards. Lesson and state paths are local and Git-ignored. Use separate state files and Anki decks for separate learning profiles.

Each due batch contributes up to two active-recall questions, capped at twelve per day. Overdue lower-priority terms remain queued. Answers appear at the end of the lesson. **The app does not infer whether you answered correctly from the displayed answer key.** Record actual results:

```powershell
domain-vocab-anki grade --term "gearbox housing" --correct
domain-vocab-anki grade --term "planetary stage" --incorrect
domain-vocab-anki status
```

An incorrect term restarts at D+1 and is marked for reinforcement. Two consecutive correct recorded answers restore its original schedule. A term's first study date, review attempts, and status stay in the local SQLite file. Use `--date YYYY-MM-DD` for deterministic tests or catching up; do not backdate real grades casually.

## 4. Anki setup

Install and enable [AnkiConnect](https://ankiweb.net/shared/info/2055492159), then keep the Anki desktop app open for a live sync. The configured note type must have the named `Front` and `Back` fields; the example uses Anki's `Basic` type. **Front is only the English term. Back contains the IPA, part of speech, Chinese meaning, usage context, English example, Chinese translation, collocation/error note, and first-study date.** The sync checks existing notes in the target deck to avoid duplicate terms. If Anki is closed, cards stay queued and the next `run` or `sync` retries them. The app does not invoke AnkiWeb sync; use Anki's own sync if desired.

## 5. 每天 09:00 自动运行 / Daily scheduling

On Windows, after editing your profile and installing the package, run:

```powershell
.\scripts\install_windows_task.ps1 -ConfigPath (Resolve-Path .\examples\custom-domain.json) -At '09:00'
```

This registers a local Windows Task Scheduler task for every day, including weekends. Logs go to `logs/YYYY-MM-DD.log`. See [scheduling details](docs/scheduling.md) for macOS/Linux and the optional Codex reminder workflow. Anki must be running to sync immediately; the local queue handles offline days.

## Safety and privacy

This repository contains **sample data only**. It does not include the original learner's Anki collection, card exports, answer history, API key, or private company material. Before using generated customer-facing copy, verify technical figures, certifications, delivery promises, pricing, and customer claims. The validator enforces structure and duplicate avoidance; it cannot independently prove business facts.

## Development

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

MIT licensed. Contributions for new domains, more review question types, and additional card templates are welcome.
