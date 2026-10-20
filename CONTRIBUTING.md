# Contributing

## Local setup

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
```

Run the complete local quality gate before opening a pull request:

```bash
python scripts/check_text.py
ruff check .
mypy src
pytest
```

Changes to model behavior must include an evaluation fixture or a recorded experiment. Do not commit credentials, personal data, employer data, generated artifacts larger than needed for review, or data without a clear license.

