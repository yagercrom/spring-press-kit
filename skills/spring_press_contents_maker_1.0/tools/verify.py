"""Check a generated press release before it goes out.

Exits non-zero when something is wrong, so this can gate a hand-off. The three
things worth checking are the ones that fail silently: a table whose declared
row count drifted (Hancom refuses to open the file), a missing table (the plan
had one but generation dropped it), and reference sentences left behind because
a plan block was omitted.

Usage:
    python "<SKILL_DIR>/tools/verify.py" 보도자료.hwpx
    python "<SKILL_DIR>/tools/verify.py" 보도자료.hwpx --expect-tables 7
"""

import argparse
import re
import sys
import zipfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# The hwpx skill supplies every HWPX primitive. It normally sits beside this
# skill; fall back to the conventional user-scope location so the script also
# works when this skill is installed on its own.
_CANDIDATES = [
    SKILL_DIR.parent / "hwpx",
    Path.home() / ".claude" / "skills" / "hwpx",
]
for _candidate in _CANDIDATES:
    if (_candidate / "scripts" / "read_hwpx.py").exists():
        sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit(
        "hwpx skill not found. Looked in:\n  "
        + "\n  ".join(str(c) for c in _CANDIDATES)
        + "\nInstall the hwpx skill (it ships alongside this one) and retry."
    )

from scripts import read_hwpx, table_fixer  # noqa: E402

# Sentences that only exist in assets/press-release-reference.hwpx. Finding any
# of them in the output means a plan block was missing and the donor's own text
# was left in place.
# Pick strings that no plausible plan would legitimately contain -- company names
# and table captions from the donor's own tables. A marker that a real plan might
# reuse (a sentence about the donor's own subject matter) produces false alarms
# and trains people to ignore this check.
REFERENCE_MARKERS = [
    "면접전형 운영 요소",
    "한국수력원자력",
    "제주국제자유도시개발센터",
    "NCS 직업기초능력평가 주요 평가영역",
    "서류전형에서 어학성적 영향력",
]

PLACEHOLDERS = ["{TEXT}", "{CHAR_PR_ID}", "{PARA_PR_ID}"]


def main():
    parser = argparse.ArgumentParser(description="Verify a generated press release HWPX")
    parser.add_argument("path", help="Path to the generated .hwpx")
    parser.add_argument(
        "--expect-tables",
        type=int,
        default=None,
        help="Expected table count (3 boxes + one per data table)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        sys.exit(f"not found: {path}")

    failures = []
    doc = read_hwpx.open_hwpx(path)
    summary = doc.get_structure_summary()

    print(f"=== {path.name} ===")
    print(f"  sections   : {summary['section_count']}")
    print(f"  tables     : {summary['table_count']}")
    print(f"  images     : {summary['image_count']}")
    print(f"  styles     : {summary['styles']}")

    if args.expect_tables is not None and summary["table_count"] != args.expect_tables:
        failures.append(
            f"table count is {summary['table_count']}, expected {args.expect_tables}"
        )

    print("\n  table consistency (rowCnt / cellAddr / rowAddr)")
    for name in doc.list_sections():
        section_xml = doc.get_entry_text(name)
        errors = table_fixer.validate_all_tables(section_xml)
        print(f"    {name}: {len(errors)} error(s)")
        for err in errors:
            print(f"      {err}")
        if errors:
            failures.append(f"{name} has {len(errors)} table consistency error(s)")

    full_text = "\n".join(
        doc.get_entry_text(name) for name in doc.list_sections()
    )

    print("\n  leftover reference text")
    for marker in REFERENCE_MARKERS:
        hits = full_text.count(marker)
        print(f"    {marker!r}: {hits}")
        if hits:
            failures.append(f"reference text left in output: {marker!r}")

    print("\n  unrendered placeholders")
    for token in PLACEHOLDERS:
        hits = full_text.count(token)
        print(f"    {token}: {hits}")
        if hits:
            failures.append(f"unrendered placeholder in output: {token}")

    print("\n  ZIP invariants")
    with zipfile.ZipFile(path) as zf:
        entries = zf.infolist()
        first = entries[0]
        print(f"    first entry     : {first.filename}")
        print(f"    first is STORED : {first.compress_type == zipfile.ZIP_STORED}")
        print(f"    CRC failures    : {zf.testzip()}")
        if first.filename != "mimetype":
            failures.append("mimetype is not the first ZIP entry")
        if first.compress_type != zipfile.ZIP_STORED:
            failures.append("mimetype is not stored uncompressed")
        if zf.testzip() is not None:
            failures.append("ZIP CRC check failed")

    # Line geometry: every lineseg's vertpos should step by vertsize + spacing.
    bad_geometry = 0
    for arr in re.findall(r"<hp:linesegarray>.*?</hp:linesegarray>", full_text, re.DOTALL):
        segs = re.findall(r"<hp:lineseg\b[^/>]*/>", arr)
        for index, seg in enumerate(segs):
            attrs = dict(re.findall(r'(\w+)="(-?\d+)"', seg))
            if not {"vertpos", "vertsize", "spacing"} <= attrs.keys():
                continue
            step = int(attrs["vertsize"]) + int(attrs["spacing"])
            if int(attrs["vertpos"]) != index * step:
                bad_geometry += 1
    print(f"\n  line geometry mismatches: {bad_geometry}")
    if bad_geometry:
        failures.append(f"{bad_geometry} lineseg(s) have unexpected vertpos")

    if failures:
        print("\nFAIL")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
