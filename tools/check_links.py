#!/usr/bin/env python3
"""Проверка битых внутренних ссылок: пути, на которые ссылаются
course.yaml и markdown-файлы, но которых нет на диске.

Два независимых источника проверок:
  1. Структурные поля course.yaml (labs[].path, materials[]) — читаются
     из YAML напрямую, ложных срабатываний не даёт. Плюс: если
     labs[].autograded — в пути обязателен check.sh.
  2. Markdown-файлы репозитория (кроме research/raw и research/md —
     заимствованный/производный архив, не место для внутренних ссылок
     этой программы): в этом репозитории ссылки на файлы пишутся не
     синтаксисом `[текст](путь)` (он не встречается вовсе), а обратными
     кавычками — `docs/HOW-TO-RUN-LABS.md`, `tools/run-check.sh` и т.п.
     Эвристика: содержимое в обратных кавычках считается путём, только
     если это './'/'../'-относительный путь (резолвится от каталога
     самого файла) либо начинается с реального каталога/файла верхнего
     уровня репозитория (program, labs, docs, tools, ...) — это отсекает
     команды, флаги, идентификаторы кода и типы сообщений ROS2 вида
     `sensor_msgs/msg/Image` (msg-типы, "sensor_msgs" не каталог
     репозитория), но пропускает реальные пути. Эвристика неполная (не
     ловит ссылки без обратных кавычек, не проверяет орфографию рядом
     с путём) — не замена ручному ревью, но ловит явные расхождения.

Пути, которых по design нет на диске (bind-mount labs/env/workspace/,
read-only архив research/raw/ и т.п. — см. .gitignore), не считаются
битыми ссылками: сверяются с .gitignore, а не с фиксированным списком
исключений в этом файле. './'-относительные упоминания (в основном —
"Использование: ./check.sh" после cd в другую директорию, не ссылка на
файл рядом с самим md-файлом) и шаблонные плейсхолдеры вида
program/cohorts/{ID}.md тоже пропускаются.

Exit code: 0 — ок; 1 — есть битые ссылки.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COURSES = ROOT / "program" / "courses"

# Каталоги, где markdown не сканируется вообще (не внутренние ссылки
# программы: read-only архив The Construct и его производный пересказ).
SKIP_MD_DIRS = {"research/raw", "research/md"}

TOP_LEVEL = {p.name for p in ROOT.iterdir() if p.name != ".git"}

BACKTICK_RE = re.compile(r"`([^`\s]+)`")
TRAILING_PUNCT = ")>,.:;\"'"


def load_gitignore_dirs() -> set[str]:
    """Каталоги, явно перечисленные в .gitignore (без начального/конечного
    '/'). Их отсутствие на диске ожидаемо — это не битая ссылка, а
    сгенерированные/несинхронизируемые данные (bind-mount, архив и т.п.)."""
    dirs = set()
    gi = ROOT / ".gitignore"
    for line in gi.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or not line.endswith("/"):
            continue
        dirs.add(line.strip("/"))
    return dirs


GITIGNORED_DIRS = load_gitignore_dirs()


def is_expected_absent(rel_target: str) -> bool:
    t = rel_target.rstrip("/")
    return any(t == d or t.startswith(d + "/") for d in GITIGNORED_DIRS)


def should_skip_md(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(rel == d or rel.startswith(d + "/") for d in SKIP_MD_DIRS)


def iter_md_files():
    for p in sorted(ROOT.rglob("*.md")):
        if ".git" in p.parts:
            continue
        if should_skip_md(p):
            continue
        yield p


def normalize_candidate(raw: str) -> str | None:
    s = raw.split("#", 1)[0]  # отрезать якорь заголовка, если есть
    s = s.rstrip(TRAILING_PUNCT)
    if not s or " " in s:
        return None
    if s.startswith(("/", "~", "$", "-", "./", "../")):
        return None
    if any(c in s for c in "<>*{}"):
        return None
    return s


def resolve_candidate(raw: str) -> Path | None:
    """Возвращает путь на диске, если raw похож на внутреннюю ссылку
    этого репозитория, иначе None (не путь / внешняя ссылка / не наш
    формат — не ошибка, просто не проверяем). './'-относительные
    упоминания намеренно не резолвятся: в этом репозитории они почти
    всегда часть команды («cd лаба && ./check.sh»), не ссылка на файл
    рядом с md-файлом, где встречается упоминание."""
    s = normalize_candidate(raw)
    if s is None or "/" not in s:
        return None  # нет './'/'../' и нет каталога — слишком неоднозначно
    first = s.split("/", 1)[0]
    if first not in TOP_LEVEL:
        return None  # не начинается с реального каталога/файла репозитория
    return (ROOT / s).resolve()


def check_markdown_links() -> list[str]:
    errors = []
    for f in iter_md_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        rel_f = f.relative_to(ROOT).as_posix()
        seen = set()
        for m in BACKTICK_RE.finditer(text):
            raw = m.group(1)
            target = resolve_candidate(raw)
            if target is None or target.exists():
                continue
            if is_expected_absent(target.relative_to(ROOT).as_posix()):
                continue
            key = (rel_f, raw)
            if key in seen:
                continue
            seen.add(key)
            errors.append(f"{rel_f}: ссылается на несуществующий путь `{raw}`")
    return errors


def check_course_yaml() -> list[str]:
    errors = []
    for cy in sorted(COURSES.glob("*/course.yaml")):
        cid = cy.parent.name
        data = yaml.safe_load(cy.read_text(encoding="utf-8")) or {}
        for lab in data.get("labs") or []:
            lp = lab.get("path")
            if not lp:
                continue
            target = ROOT / lp
            if not target.is_dir():
                errors.append(f"{cid}/course.yaml: labs[{lab.get('id')}].path "
                              f"-> не существует «{lp}»")
                continue
            if lab.get("autograded") and not (target / "check.sh").exists():
                errors.append(f"{cid}/course.yaml: labs[{lab.get('id')}] "
                               f"autograded: true, но нет {lp}/check.sh")
        for mat in data.get("materials") or []:
            if not (ROOT / mat).exists():
                errors.append(f"{cid}/course.yaml: materials -> не существует «{mat}»")
    return errors


def main() -> int:
    errors = check_course_yaml() + check_markdown_links()
    print(f"Проверено course.yaml: {len(list(COURSES.glob('*/course.yaml')))}, "
          f"markdown-файлов: {len(list(iter_md_files()))}. Битых ссылок: {len(errors)}.")
    for e in errors:
        print("  -", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
