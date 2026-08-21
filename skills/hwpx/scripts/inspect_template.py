"""Enumerate every text node in an HWPX so placeholders can be identified.

Filling a template starts with knowing what text is actually in it. Guessing
placeholder strings and calling replace_text() on a guess fails silently: the
replacement count is zero, the file still opens fine, and the wrong document
ships. This module makes the inventory explicit and countable instead.

Text is reported per section with the paragraph index it belongs to, because
modify_hwpx addresses paragraphs by index, not by pattern. Repeated strings are
grouped with their occurrence count -- a count above 1 means a single
replace_text() call would overwrite every copy, so use max_count to fill them
one at a time.

Usage:
    cd <SKILL_DIR>
    python -m scripts.inspect_template <file.hwpx>
    python -m scripts.inspect_template <file.hwpx> --repeated-only
"""

import argparse
import re
import sys
from collections import Counter, OrderedDict

from . import read_hwpx

# <hp:t> is the text node; the prefix is not guaranteed, so match any.
_TEXT_NODE = re.compile(r"<(?:\w+:)?t(?:\s[^>]*)?>(.*?)</(?:\w+:)?t>", re.DOTALL)


def extract_texts(section_xml):
    """Return the non-empty text node values of one section, in document order."""
    out = []
    for match in _TEXT_NODE.finditer(section_xml):
        value = match.group(1)
        if value.strip():
            out.append(value)
    return out


def inspect(path):
    """Return {section_name: [text, ...]} for every section of the document."""
    doc = read_hwpx.open_hwpx(path)
    result = OrderedDict()
    for name in doc.list_sections():
        result[name] = extract_texts(doc.get_entry_text(name))
    return result


def report(path, repeated_only=False):
    per_section = inspect(path)
    totals = Counter()
    for texts in per_section.values():
        totals.update(texts)

    for name, texts in per_section.items():
        shown = [t for t in texts if not repeated_only or totals[t] > 1]
        print(f"\n=== {name} ({len(texts)} text nodes) ===")
        seen = Counter()
        for text in shown:
            seen[text] += 1
            total = totals[text]
            marker = f"  [{seen[text]}/{total}]" if total > 1 else ""
            print(f"  {text!r}{marker}")

    repeated = {t: c for t, c in totals.items() if c > 1}
    nested = [t for t in totals if "<" in t]
    print(f"\n=== summary ===")
    print(f"  distinct strings : {len(totals)}")
    print(f"  repeated strings : {len(repeated)}")
    if repeated:
        print("  repeated (fill these with max_count, one at a time):")
        for text, count in sorted(repeated.items(), key=lambda kv: -kv[1]):
            print(f"    {count}x  {text!r}")
    if nested:
        print("  nested markup -- replace only the literal text you want,")
        print("  never the whole value, or the inner element is destroyed:")
        for text in nested:
            print(f"    {text!r}")


def main():
    parser = argparse.ArgumentParser(
        description="List all text nodes in an HWPX to identify placeholders"
    )
    parser.add_argument("path", help="Path to the .hwpx file")
    parser.add_argument(
        "--repeated-only",
        action="store_true",
        help="Show only strings that occur more than once",
    )
    args = parser.parse_args()
    report(args.path, repeated_only=args.repeated_only)


if __name__ == "__main__":
    main()
