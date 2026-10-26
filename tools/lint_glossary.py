#!/usr/bin/env python3
"""Терминологический линтер.

Проверяет контент на запрещённые варианты перевода из program/glossary.yaml.
По умолчанию курсы со status: draft|deprecated пропускаются (их описания —
непереработанное сырьё); флаг --all проверяет всё, --report печатает сводку
без ненулевого кода выхода.

Exit code: 0 — чисто; 1 — найдены нарушения.
Использование:
    python tools/lint_glossary.py                  # gate для CI
    python tools/lint_glossary.py --all --report   # полная инвентаризация
    python tools/lint_glossary.py path/to/file.md  # конкретные файлы (для hook)
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
GLOSSARY = ROOT / "program" / "glossary.yaml"
SCAN_DIRS = [ROOT / "program", ROOT / "research" / "md"]
EXTS = {".md", ".yaml", ".yml"}


def load_forbidden() -> list[tuple[str, str, re.Pattern]]:
    entries = yaml.safe_load(GLOSSARY.read_text(encoding="utf-8")) or []
    pats = []
    for e in entries:
        for f in e.get("forbidden") or []:
            f = f.strip()
            if f:
                pats.append((e["en"], f, re.compile(re.escape(f), re.IGNORECASE)))
    return pats


def course_status(path: Path) -> str | None:
    """Для файлов внутри program/courses/<id>/ вернуть status из course.yaml."""
    for parent in path.parents:
        cy = parent / "course.yaml"
        if cy.exists():
            try:
                return (yaml.safe_load(cy.read_text(encoding="utf-8")) or {}).get("status")
            except Exception:
                return None
    return None


def iter_targets(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(p).resolve() for p in explicit if Path(p).suffix in EXTS]
    out = []
    for d in SCAN_DIRS:
        if d.exists():
            out += [p for p in d.rglob("*") if p.suffix in EXTS and p != GLOSSARY]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--all", action="store_true", help="не пропускать draft/deprecated")
    ap.add_argument("--report", action="store_true", help="только отчёт, exit 0")
    args = ap.parse_args()

    patterns = load_forbidden()
    violations: list[tuple[Path, int, str, str]] = []
    skipped = 0

    for path in iter_targets(args.files):
        if not args.all and not args.files:
            st = course_status(path)
            if st in ("draft", "deprecated"):
                skipped += 1
                continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            for term_en, forb, pat in patterns:
                if pat.search(line):
                    violations.append((path, i, forb, term_en))

    for path, line, forb, term in violations:
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        print(f"{rel}:{line}: запрещённый вариант «{forb}» (термин: {term})")

    print(f"\nПроверено с пропуском {skipped} draft/deprecated файлов. "
          f"Нарушений: {len(violations)}.")
    if args.report:
        return 0
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
