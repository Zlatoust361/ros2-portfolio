#!/usr/bin/env python3
"""Валидация программы: схема course.yaml + граф пререквизитов.

Проверки:
  1. Каждый course.yaml соответствует program/schema/course.schema.json.
  2. id совпадает с именем каталога.
  3. Все prerequisites и supersedes ссылаются на существующие id.
  4. Пререквизиты active-курсов не указывают на deprecated.
  5. Граф пререквизитов ацикличен.

Exit code: 0 — ок; 1 — есть ошибки.
Флаг --mermaid печатает диаграмму графа (active-курсы).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
COURSES = ROOT / "program" / "courses"
SCHEMA = json.loads((ROOT / "program" / "schema" / "course.schema.json").read_text(encoding="utf-8"))


def strip_aux(d: dict) -> dict:
    d = dict(d)
    d.pop("migrated", None)  # вспомогательное поле миграции
    return d


def load_all() -> dict[str, dict]:
    out = {}
    for cy in sorted(COURSES.glob("*/course.yaml")):
        data = yaml.safe_load(cy.read_text(encoding="utf-8")) or {}
        out[cy.parent.name] = data
    return out


def main() -> int:
    mermaid = "--mermaid" in sys.argv
    validator = Draft202012Validator(SCHEMA)
    courses = load_all()
    errors: list[str] = []

    for dirname, data in courses.items():
        for err in validator.iter_errors(strip_aux(data)):
            errors.append(f"{dirname}/course.yaml: {err.message} (путь: {'/'.join(map(str, err.path))})")
        if data.get("id") != dirname:
            errors.append(f"{dirname}: id «{data.get('id')}» не совпадает с именем каталога")

    ids = set(courses)
    for cid, data in courses.items():
        for ref_field in ("supersedes",):
            ref = data.get(ref_field)
            if ref and ref not in ids:
                errors.append(f"{cid}: {ref_field} -> несуществующий id «{ref}»")
        for pre in data.get("prerequisites") or []:
            if pre not in ids:
                errors.append(f"{cid}: prerequisite -> несуществующий id «{pre}»")
            elif data.get("status") != "deprecated" and courses[pre].get("status") == "deprecated":
                errors.append(f"{cid}: prerequisite «{pre}» является deprecated")

    # Поиск циклов (DFS по active-графу).
    graph = {cid: [p for p in (d.get("prerequisites") or []) if p in ids]
             for cid, d in courses.items()}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(graph, WHITE)

    def dfs(u: str, stack: list[str]) -> None:
        color[u] = GRAY
        stack.append(u)
        for v in graph[u]:
            if color[v] == GRAY:
                cyc = stack[stack.index(v):] + [v]
                errors.append("цикл пререквизитов: " + " -> ".join(cyc))
            elif color[v] == WHITE:
                dfs(v, stack)
        stack.pop()
        color[u] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node, [])

    if mermaid:
        print("```mermaid\ngraph TD")
        for cid, d in courses.items():
            if d.get("status") == "deprecated":
                continue
            for pre in d.get("prerequisites") or []:
                print(f"  {pre} --> {cid}")
        print("```")

    active = sum(1 for d in courses.values() if d.get("status") != "deprecated")
    print(f"Курсов: {len(courses)} (active: {active}, deprecated: {len(courses)-active}). "
          f"Ошибок: {len(errors)}.")
    for e in errors:
        print("  -", e)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
