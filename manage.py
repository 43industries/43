from __future__ import annotations

import argparse
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "submissions.json"


def load_submissions() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def cmd_list(args: argparse.Namespace) -> None:
    items = load_submissions()
    if not items:
        print("No submissions.")
        return
    for s in items:
        print(f"#{s.get('id')} {s.get('name')} <{s.get('email')}> - {s.get('subject')}")


def cmd_clear(args: argparse.Namespace) -> None:
    if DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")
    print("Submissions cleared.")


def cmd_count(args: argparse.Namespace) -> None:
    items = load_submissions()
    print(len(items))


def main() -> None:
    parser = argparse.ArgumentParser(description="43 Industries management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub_list = sub.add_parser("list-submissions", help="List all contact submissions")
    sub_list.set_defaults(func=cmd_list)

    sub_clear = sub.add_parser("clear-submissions", help="Delete all submissions")
    sub_clear.set_defaults(func=cmd_clear)

    sub_count = sub.add_parser("count-submissions", help="Show submission count")
    sub_count.set_defaults(func=cmd_count)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

