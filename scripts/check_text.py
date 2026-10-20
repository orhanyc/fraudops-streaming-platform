from pathlib import Path

TEXT_SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml", ".txt", ".json"}
IGNORED_PARTS = {".git", ".venv", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def main() -> None:
    failures: list[str] = []
    for path in Path(".").rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        if "\u2014" in path.read_text(encoding="utf-8"):
            failures.append(str(path))
    if failures:
        raise SystemExit("Em dash found in: " + ", ".join(failures))
    print("Text policy passed")


if __name__ == "__main__":
    main()
