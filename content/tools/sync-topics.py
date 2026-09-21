#!/usr/bin/env python3
"""Synchronize content/topics.json from bilingual article JSON files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTENT_DIR = REPO_ROOT / "content"
TOPICS_FILE = CONTENT_DIR / "topics.json"
ARTICLES_DIR = CONTENT_DIR / "articles"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_articles(language: str) -> dict[int, tuple[dict, Path]]:
    items: dict[int, tuple[dict, Path]] = {}
    directory = ARTICLES_DIR / language
    for path in sorted(directory.glob("*.json")):
        data = read_json(path)
        number = int(data["article_number"])
        if number in items:
            raise SystemExit(f"Duplicate article number {number} in {language}: {path}")
        if data.get("language") != language:
            raise SystemExit(f"{path}: language field does not match directory")
        items[number] = (data, path)
    return items


def primary_taxonomy(article: dict, key: str, fallback: str) -> str:
    value = article.get("taxonomy", {}).get(key, {}).get("primary")
    return str(value or fallback)


def derive_intent(section: str) -> str:
    if section == "learn":
        return "informational"
    if section == "buying-guides":
        return "commercial"
    if section == "ideas":
        return "commercial"
    return "informational"


def normalized_status(es: dict, en: dict, number: int) -> str:
    es_status = str(es.get("status", "draft"))
    en_status = str(en.get("status", "draft"))
    if es_status != en_status:
        raise SystemExit(
            f"Article {number}: ES/EN status mismatch ({es_status!r} vs {en_status!r})"
        )
    return "published" if es_status == "publish" else es_status


def build_topics(existing_doc: dict) -> dict:
    es_articles = load_articles("es")
    en_articles = load_articles("en")

    es_numbers = set(es_articles)
    en_numbers = set(en_articles)
    if es_numbers != en_numbers:
        only_es = sorted(es_numbers - en_numbers)
        only_en = sorted(en_numbers - es_numbers)
        raise SystemExit(
            f"Bilingual article mismatch. Only ES: {only_es}; only EN: {only_en}"
        )

    existing_by_number = {
        int(item["number"]): item for item in existing_doc.get("topics", [])
    }

    topics: list[dict] = []
    for number in sorted(es_numbers):
        es, es_path = es_articles[number]
        en, en_path = en_articles[number]

        if es.get("translation_group") != en.get("translation_group"):
            raise SystemExit(
                f"Article {number}: translation_group mismatch in {es_path} and {en_path}"
            )

        section = primary_taxonomy(es, "section", "learn")
        topic = primary_taxonomy(es, "topic", "cross-stitch")
        craft = primary_taxonomy(es, "craft", "cross-stitch")

        en_section = primary_taxonomy(en, "section", section)
        en_topic = primary_taxonomy(en, "topic", topic)
        en_craft = primary_taxonomy(en, "craft", craft)
        if (section, topic, craft) != (en_section, en_topic, en_craft):
            raise SystemExit(
                f"Article {number}: ES/EN taxonomy mismatch "
                f"({section}/{topic}/{craft} vs {en_section}/{en_topic}/{en_craft})"
            )

        previous = existing_by_number.get(number, {})
        topics.append(
            {
                "number": number,
                "priority": previous.get("priority", "P3"),
                "section": section,
                "topic": topic,
                "intent": previous.get("intent", derive_intent(section)),
                "status": normalized_status(es, en, number),
                "title_es": es["title"],
                "title_en": en["title"],
                "craft": craft,
            }
        )

    result = dict(existing_doc)
    result["topics"] = topics
    result["index_management"] = {
        "source_of_truth": [
            "content/articles/es/*.json",
            "content/articles/en/*.json",
        ],
        "sync_script": "content/tools/sync-topics.py",
        "auto_sync_workflow": ".github/workflows/import-articles.yml",
        "policy": (
            "The article JSON pairs are the source of truth. topics.json is a "
            "synchronized editorial index updated after successful imports."
        ),
        "last_indexed_article": max(es_numbers) if es_numbers else 0,
        "bilingual_groups": len(topics),
    }
    return result


def render(doc: dict) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if topics.json is not synchronized.",
    )
    args = parser.parse_args()

    current_text = TOPICS_FILE.read_text(encoding="utf-8")
    current_doc = json.loads(current_text)
    expected_text = render(build_topics(current_doc))

    if args.check:
        if current_text != expected_text:
            print("content/topics.json is out of sync", file=sys.stderr)
            return 1
        print("content/topics.json is synchronized")
        return 0

    if current_text == expected_text:
        print("content/topics.json already synchronized")
        return 0

    TOPICS_FILE.write_text(expected_text, encoding="utf-8")
    updated = json.loads(expected_text)
    print(
        "Synchronized "
        f"{updated['index_management']['bilingual_groups']} bilingual topic groups "
        f"through article {updated['index_management']['last_indexed_article']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
