#!/usr/bin/env python3
"""
build.py — Renders Jinja2 templates for arunadvani.com.

Reads data/papers.json and templates/, writes output HTML files to the
project root (ready for GitHub Pages).

Usage:
    python build.py
"""

import json
import re
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "templates"
DATA_FILE = ROOT / "papers.json"
OUTPUT_DIR = ROOT  # GitHub Pages serves from the repo root

# ---------------------------------------------------------------------------
# Topic configuration
# ---------------------------------------------------------------------------

# Display order for the by-topic page.  id → human-readable name is derived
# by inserting spaces before uppercase letters (camelCase → Title Case).
TOPIC_ORDER = [
    "TaxDesign",
    "Migration",
    "IncomeInequality",
    "WealthInequality",
    "TaxCompliance",
    "Ethnicity",
    "Education",
    "Environment",
    "Development",
    "Econometrics",
]


def topic_display_name(topic_id: str) -> str:
    """Convert camelCase topic id to a human-readable name.

    e.g. "TaxDesign" → "Tax Design", "IncomeInequality" → "Income Inequality"
    """
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", topic_id)


# ---------------------------------------------------------------------------
# Data loading and preparation
# ---------------------------------------------------------------------------

def load_papers() -> list[dict]:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def prepare_entry(entry: dict) -> dict:
    """Transform a raw JSON entry into the shape the templates expect."""
    paper = dict(entry)  # shallow copy

    # ungated_url → inject into links list with label "ungated"
    if paper.get("ungated_url"):
        paper.setdefault("links", [])
        paper["links"] = [{"label": "ungated", "url": paper["ungated_url"]}] + paper["links"]

    # media: flat list → {"coverage": [...], "opeds": [...]}
    # op-eds are identified by "(op-ed)" in the outlet name
    media = paper.get("media")
    if media and isinstance(media, list) and len(media) > 0:
        coverage = [m for m in media if "(op-ed)" not in m.get("outlet", "").lower()]
        opeds = [
            {**m, "outlet": m["outlet"].replace(" (op-ed)", "").replace("(op-ed)", "").strip()}
            for m in media
            if "(op-ed)" in m.get("outlet", "").lower()
        ]
        paper["media"] = {"coverage": coverage, "opeds": opeds}
    else:
        paper["media"] = None

    # Ensure topics is a list (guard against null)
    if paper.get("topics") is None:
        paper["topics"] = []

    return paper


def sorted_by_order(entries: list[dict]) -> list[dict]:
    """Sort entries by the 'order' field, descending (highest first)."""
    return sorted(entries, key=lambda e: e.get("order", 0), reverse=True)


def filter_entries(entries: list[dict], page: str, section: str) -> list[dict]:
    """Return entries matching a given page and section, sorted by order."""
    return sorted_by_order([
        e for e in entries
        if page in e.get("pages", []) and e.get(f"{page}_section") == section
    ])


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        keep_trailing_newline=True,
    )

    # Load and prepare all entries
    raw_entries = load_papers()
    entries = [prepare_entry(e) for e in raw_entries]

    # --- research.html ---
    research_template = env.get_template("research.html")
    research_html = research_template.render(
        working_papers=filter_entries(entries, "research", "working_paper"),
        published_papers=filter_entries(entries, "research", "published"),
        older_papers=filter_entries(entries, "research", "older"),
    )
    (OUTPUT_DIR / "research.html").write_text(research_html, encoding="utf-8")
    print("  research.html")

    # --- policy.html ---
    policy_template = env.get_template("policy.html")
    policy_html = policy_template.render(
        policy_papers=filter_entries(entries, "policy", "policy_paper"),
        comments=filter_entries(entries, "policy", "comment_oped"),
        consultations=filter_entries(entries, "policy", "consultation"),
    )
    (OUTPUT_DIR / "policy.html").write_text(policy_html, encoding="utf-8")
    print("  policy.html")

    # --- researchbytopic.html ---
    # Build the topics list in defined order
    topics = []
    for topic_id in TOPIC_ORDER:
        topic_papers = sorted_by_order([
            e for e in entries
            if topic_id in e.get("topics", [])
        ])
        if topic_papers:  # only include topics that have entries
            topics.append({
                "id": topic_id,
                "name": topic_display_name(topic_id),
                "papers": topic_papers,
            })

    # Warn about any topics in the data that aren't in TOPIC_ORDER
    all_topics_in_data = set()
    for e in entries:
        for t in e.get("topics", []):
            all_topics_in_data.add(t)
    unknown = all_topics_in_data - set(TOPIC_ORDER)
    if unknown:
        print(f"  WARNING: topics in data but not in TOPIC_ORDER: {unknown}")

    bytopic_template = env.get_template("researchbytopic.html")
    bytopic_html = bytopic_template.render(topics=topics)
    (OUTPUT_DIR / "researchbytopic.html").write_text(bytopic_html, encoding="utf-8")
    print("  researchbytopic.html")

    # --- index.html ---
    index_template = env.get_template("index.html")
    index_html = index_template.render()
    (OUTPUT_DIR / "index.html").write_text(index_html, encoding="utf-8")
    print("  index.html")

    # --- taxreform.html ---
    taxreform_template = env.get_template("taxreform.html")
    taxreform_html = taxreform_template.render()
    (OUTPUT_DIR / "taxreform.html").write_text(taxreform_html, encoding="utf-8")
    print("  taxreform.html")


if __name__ == "__main__":
    print("Building site...")
    build()
    print("Done.")
