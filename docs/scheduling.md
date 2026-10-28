# Local scheduling

The scheduler must run on the same computer as AnkiConnect (`127.0.0.1:8765`). A cloud CI runner cannot directly reach your local Anki desktop session. GitHub Actions in this repository runs tests only.

## Windows

Install the package first. Then use `scripts/install_windows_task.ps1` with an absolute profile path. The script schedules `scripts/run_daily.ps1` at 09:00 every day, including weekends, and enables "start when available". The runner writes lessons to `lessons/`, state to `state/learning.sqlite3`, and daily logs to `logs/` in the project directory. These files are excluded from Git.

To inspect the task, open Task Scheduler and find `DomainVocabAnkiDaily`. To remove it: `Unregister-ScheduledTask -TaskName DomainVocabAnkiDaily -Confirm:$false`.

Use a private profile copy. Ensure the Python environment used by the scheduled task has the package installed and, for AI mode, can read `OPENAI_API_KEY` from the local user environment. If Anki is closed at 09:00, run `domain-vocab-anki sync --config YOUR_PROFILE` after opening it, or let the next daily run retry.

## Linux cron

Use absolute paths and a Python interpreter with the package installed. Example crontab entry (system local time):

```cron
0 9 * * * /absolute/path/to/.venv/bin/python -m domain_vocab_anki.cli run --config /absolute/private/profile.json --state /absolute/private/learning.sqlite3 --output /absolute/private/lessons >> /absolute/private/daily.log 2>&1
```

## macOS launchd

Create a user LaunchAgent that runs the same absolute Python command daily at hour 9 using `StartCalendarInterval` with `Hour=9` and `Minute=0`. Put profile, state, output and log paths in your home directory. The user session must be active to reach AnkiConnect.

## Codex automation (optional)

If you already use a Codex daily lesson task, keep it as a lesson notification or review companion. The local scheduled command above is the reliable path for direct access to AnkiConnect and SQLite. Avoid creating a second independent source of new words for the same day: use the generated `lessons/YYYY-MM-DD.md` as the single lesson record.
