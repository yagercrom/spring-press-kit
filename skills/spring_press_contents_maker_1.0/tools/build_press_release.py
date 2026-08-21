"""Build a 교육의봄 press release HWPX from a JSON plan.

Why a generator instead of hand-assembled XML: the press release look lives in
header.xml style IDs (fonts, sizes, indents) that only exist inside a real
Hancom-saved document. So every paragraph this script emits is a clone of a
paragraph in assets/press-release-reference.hwpx, with the text swapped. Styles
are therefore correct by construction rather than by transcription.

Roles are located in the reference by marker text, never by paragraph index --
indices shift the moment anything is inserted.

This lives in tools/ rather than scripts/ on purpose: the hwpx skill exposes its
primitives as a package literally named `scripts`, so a sibling `scripts/` here
would shadow it and the imports below would fail.

Usage:
    python "<SKILL_DIR>/tools/build_press_release.py" --plan plan.json --output out.hwpx

The plan schema is documented in references/plan-schema.md; examples/ has
working plans.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
REFERENCE = SKILL_DIR / "assets" / "press-release-reference.hwpx"

# The hwpx skill owns all HWPX primitives; this script only composes. Look for
# it beside this skill first so a team member who installed both together works
# without configuration, then fall back to the conventional user-scope path.
_HWPX_CANDIDATES = [
    SKILL_DIR.parent / "hwpx",
    Path.home() / ".claude" / "skills" / "hwpx",
]
for _candidate in _HWPX_CANDIDATES:
    if (_candidate / "scripts" / "read_hwpx.py").exists():
        if str(_candidate) not in sys.path:
            sys.path.insert(0, str(_candidate))
        break
else:
    sys.exit(
        "hwpx skill not found. Looked in:\n  "
        + "\n  ".join(str(c) for c in _HWPX_CANDIDATES)
        + "\nThis skill depends on it for every HWPX primitive. Install the hwpx\n"
        "skill (it ships alongside this one) and retry."
    )

from scripts import modify_hwpx, read_hwpx, table_fixer, xml_templates  # noqa: E402
from scripts._parser import find_top_level_paragraphs, find_tables  # noqa: E402
from scripts.generate_hwpx import estimate_line_breaks  # noqa: E402

# ---------------------------------------------------------------------------
# Role discovery
# ---------------------------------------------------------------------------

# role -> regex identifying a paragraph in the reference that carries that look
ROLE_MARKERS = {
    "mail_subject": r"^\[★",
    "subhead": r"^공기업들은 채용과정에서",
    "subhead_bullet": r"^- 사무직 13곳",
    "overview": r"^❏ 공공기관 블라인드 채용은",
    "result_title": r"^■ 결과 1:",
    "body": r"^먼저 분석 대상 모든 기관",
    "table_caption": r"^\s*\[표 1\]",
    "note": r"^\s*※ 어학 반영비율은",
    "position": r"^■ \(재\)교육의봄은 이번 분석",
    "closing": r"^■ 채용이 ‘대체 스펙’을",
    "publish": r"^\s*재단법인 교육의봄",
}

# 1x1 bordered boxes, in reference table order
BOX_TABLE_INDEX = {"overview_box": 0, "summary_box": 1, "implication_box": 2}
DATA_TABLE_INDEX = 3  # [표 1] -- the 구분/사무직/기술직 comparison table

_TEXT_NODE = re.compile(r"<hp:t>([^<]*)</hp:t>")

# Box slots need a second pattern. Some <hp:t> nodes in the reference wrap a
# nested element (notably <hp:lineBreak/> in the 시사점 box), and _TEXT_NODE's
# [^<]* cannot match those -- it skips them, leaving the reference's own
# sentences in the generated file. Filling a box replaces its content outright,
# so matching across nested markup is what we want here.
_BOX_SLOT = re.compile(r"<hp:t>(.*?)</hp:t>", re.DOTALL)


def _para_text(para_xml):
    return "".join(_TEXT_NODE.findall(para_xml))


def discover_roles(section_xml):
    """Map each role name to its paragraph template dict from the reference."""
    spans = find_top_level_paragraphs(section_xml)
    roles = {}
    for idx, (start, end) in enumerate(spans):
        joined = _para_text(section_xml[start:end])
        for role, pattern in ROLE_MARKERS.items():
            if role not in roles and re.search(pattern, joined):
                roles[role] = xml_templates.extract_paragraph_template(section_xml, idx)
    missing = [r for r in ROLE_MARKERS if r not in roles]
    if missing:
        raise RuntimeError(
            f"reference no longer contains marker text for roles: {missing}. "
            "The bundled reference was changed; update ROLE_MARKERS."
        )
    return roles


_LINESEG_ARRAY = re.compile(r"<hp:linesegarray>.*?</hp:linesegarray>", re.DOTALL)
_LINESEG_ATTRS = re.compile(r"<hp:lineseg\b([^/>]*)/?>")

# "estimate" predicts each visual line's start offset and emits one lineseg per
# line; "single" emits one lineseg and leaves the layout to Hancom.
#
# estimate is the default because it was checked in Hancom against the same plan
# rendered both ways, and it read correctly while single did not. Hancom does
# not fully re-flow a paragraph that declares a single segment, so the
# under-declared geometry showed as wrong line spacing. Do not flip this default
# on reasoning alone -- it was settled by looking at the rendered document.
LINESEG_MODE = "estimate"


def _seg_metrics(para_xml):
    """Read the font metrics off a paragraph's FIRST lineseg.

    vertsize/textheight/baseline/spacing differ per role (a 15pt ■ heading and a
    13pt ※ note are not the same height), so they must come from the cloned
    paragraph rather than a global default.
    """
    m = _LINESEG_ATTRS.search(para_xml)
    defaults = {
        "vertsize": 1200, "textheight": 1200, "baseline": 1020,
        "spacing": 720, "horzpos": 0, "horzsize": 48188,
        # 393216 (0x60000) is what Hancom itself writes for 552 of the 556
        # linesegs in the reference -- continuation lines included. Copying the
        # cloned paragraph's own flag keeps that convention instead of imposing
        # a different one.
        "flags": 393216,
    }
    if not m:
        return defaults
    attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    for key in defaults:
        if key in attrs:
            try:
                defaults[key] = int(attrs[key])
            except ValueError:
                pass
    return defaults


def _retime_linesegs(para_xml, text):
    """Recompute <hp:linesegarray> for the paragraph's NEW text.

    A cloned paragraph arrives carrying the reference's line geometry: one
    <hp:lineseg> per visual line of the ORIGINAL sentence, each with the
    character offset (textpos) and vertical position (vertpos) where that line
    began. Replacing the text without recomputing these leaves Hancom laying out
    new text against old coordinates, which is what makes 자간/줄간격 look
    scrambled -- the file is valid, it just renders on someone else's grid.
    """
    metrics = _seg_metrics(para_xml)
    if LINESEG_MODE == "single":
        # Fallback strategy, kept for diagnosis. Declaring one segment leaves the
        # paragraph's geometry under-described; Hancom does not fully recompute
        # it, so line spacing comes out wrong. Verified worse than "estimate".
        breaks = [0]
    else:
        # One segment per predicted visual line. Every body style here is
        # JUSTIFY, so Hancom stretches each line to the column width using the
        # character range its lineseg claims -- the geometry has to describe the
        # NEW text, not the reference sentence it was cloned from. Inheriting the
        # donor's offsets is what blew out 자간 and 줄간격.
        breaks = estimate_line_breaks(text, metrics["vertsize"], metrics["horzsize"]) or [0]
    step = metrics["vertsize"] + metrics["spacing"]

    segs = "".join(
        f'<hp:lineseg textpos="{textpos}" vertpos="{i * step}" '
        f'vertsize="{metrics["vertsize"]}" textheight="{metrics["textheight"]}" '
        f'baseline="{metrics["baseline"]}" spacing="{metrics["spacing"]}" '
        f'horzpos="{metrics["horzpos"]}" horzsize="{metrics["horzsize"]}" '
        f'flags="{metrics["flags"]}"/>'
        for i, textpos in enumerate(breaks)
    )
    fresh = f"<hp:linesegarray>{segs}</hp:linesegarray>"

    if _LINESEG_ARRAY.search(para_xml):
        return _LINESEG_ARRAY.sub(fresh, para_xml, count=1)
    # Rule: every paragraph needs a linesegarray after its runs.
    return para_xml.replace("</hp:p>", fresh + "</hp:p>", 1)


def render(role_info, text):
    """Render one paragraph in a role's style by swapping text into its clone.

    Not xml_templates.render_paragraph: that helper placeholders only the FIRST
    <hp:t> node, and several reference paragraphs are built from two runs -- the
    table caption is a charPr=51 run holding a single space followed by the
    charPr=52 run holding the actual caption. Templating the first node puts the
    new text in the spacer run, in the wrong character style, and leaves the
    reference's own sentence sitting in the second run. That is what produced
    doubled, overlapping captions.

    So: keep every run and its charPrIDRef untouched, write the text into the run
    that actually carries content (the longest text node), and blank the rest.
    """
    raw = role_info["raw"]
    nodes = list(_BOX_SLOT.finditer(raw))
    if not nodes:
        return raw

    target = max(range(len(nodes)), key=lambda i: len(nodes[i].group(1)))
    out, cursor = [], 0
    for i, m in enumerate(nodes):
        out.append(raw[cursor:m.start(1)])
        out.append(xml_escape(text) if i == target else "")
        cursor = m.end(1)
    out.append(raw[cursor:])
    return _retime_linesegs("".join(out), text)


def blank(role_info):
    return render(role_info, "")


# ---------------------------------------------------------------------------
# Boxes and tables
# ---------------------------------------------------------------------------


def fill_box(section_xml, table_index, lines):
    """Clone a 1x1 bordered box, substituting its text nodes with `lines`.

    The box's row count is fixed by the reference, so this fills what fits and
    folds any overflow into the last slot rather than dropping it. Unused slots
    become empty lines -- visible as blank rows, which is why the plan should
    keep these blocks close to the reference's length.
    """
    tables = find_tables(section_xml)
    if table_index >= len(tables):
        raise RuntimeError(f"reference has no table at index {table_index}")
    # find_tables yields (start, end, xml) -- the third element is the slice
    box = tables[table_index][2]

    slots = _BOX_SLOT.findall(box)
    if not slots:
        return box, 0

    values = list(lines)
    if len(values) > len(slots):
        head, tail = values[: len(slots) - 1], values[len(slots) - 1:]
        values = head + ["\n".join(tail)]
    values += [""] * (len(slots) - len(values))

    out, cursor, i = [], 0, 0
    for m in _BOX_SLOT.finditer(box):
        out.append(box[cursor:m.start(1)])
        out.append(xml_escape(values[i]))
        cursor = m.end(1)
        i += 1
    out.append(box[cursor:])
    filled = _retime_box_paragraphs("".join(out))
    return _drop_empty_paragraphs(filled), len(slots)


_BOX_PARA = re.compile(r"<hp:p\b[^>]*>.*?</hp:p>", re.DOTALL)


def _retime_box_paragraphs(box_xml):
    """Recompute line geometry for each paragraph inside a filled box.

    Same stale-coordinate problem as _retime_linesegs, one level down: the box's
    inner paragraphs were laid out for the reference's sentences. Their horzsize
    is the cell width rather than the page width, and _seg_metrics reads it off
    each paragraph's own first lineseg, so wrapping stays inside the border.
    """
    matches = list(_BOX_PARA.finditer(box_xml))
    out, cursor = [], 0
    for m in matches:
        chunk = m.group(0)
        if "<hp:tbl" in chunk:
            continue
        text = "".join(_BOX_SLOT.findall(chunk))
        out.append(box_xml[cursor:m.start()])
        out.append(_retime_linesegs(chunk, text))
        cursor = m.end()
    out.append(box_xml[cursor:])
    return "".join(out)


def _drop_empty_paragraphs(box_xml):
    """Remove now-empty paragraphs inside a filled box.

    A plan usually supplies fewer lines than the reference box has slots, and
    the surplus would otherwise render as a run of blank lines inside the
    border. Paragraphs carrying a table or any other element are never touched,
    and at least one paragraph is always kept because an empty cell is invalid.
    """
    matches = list(_BOX_PARA.finditer(box_xml))
    removable = []
    for m in matches:
        chunk = m.group(0)
        if "<hp:tbl" in chunk:
            continue
        texts = _BOX_SLOT.findall(chunk)
        if texts and all(not t.strip() for t in texts):
            removable.append(m)

    if len(removable) >= len(matches):
        removable = removable[:-1]  # keep one paragraph so the cell stays valid

    out, cursor = [], 0
    for m in removable:
        out.append(box_xml[cursor:m.start()])
        cursor = m.end()
    out.append(box_xml[cursor:])
    return "".join(out)


def build_table(section_xml, headers, rows):
    """Render a data table using the reference's [표 1] as the style donor."""
    tpl = xml_templates.extract_table_template(section_xml, table_index=DATA_TABLE_INDEX)
    if not tpl:
        raise RuntimeError("could not extract the reference data-table template")
    rendered = xml_templates.render_table(tpl, headers, rows)
    # Cell paragraphs are clones too, so they carry the donor cell's line
    # geometry. A short cell inheriting a two-line lineseg array renders with a
    # phantom second line, which reads as uneven row heights.
    return _retime_box_paragraphs(rendered)


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def compose_body(plan, roles, section_xml):
    """Return the list of XML fragments that make up the whole document body."""
    out = []
    add = out.append

    # --- head: mail subject line, subhead, supporting bullets ---
    add(render(roles["mail_subject"], plan["mail_subject"]))
    add(blank(roles["body"]))
    add(render(roles["subhead"], plan["subhead"]))
    add(blank(roles["body"]))
    for line in plan.get("subhead_bullets", []):
        add(render(roles["subhead_bullet"], line))
    add(blank(roles["body"]))

    # --- overview: ❏ paragraphs, then the boxed 조사 개요 ---
    for line in plan.get("overview", []):
        add(render(roles["overview"], line))
    if plan.get("overview_box"):
        box, slots = fill_box(section_xml, BOX_TABLE_INDEX["overview_box"], plan["overview_box"])
        add(box)
        _warn_slots("overview_box", plan["overview_box"], slots)
    add(blank(roles["body"]))

    # --- result summary box ---
    if plan.get("summary_lead"):
        add(render(roles["overview"], plan["summary_lead"]))
    if plan.get("summary_box"):
        box, slots = fill_box(section_xml, BOX_TABLE_INDEX["summary_box"], plan["summary_box"])
        add(box)
        _warn_slots("summary_box", plan["summary_box"], slots)

    # --- implication box ---
    if plan.get("implication_lead"):
        add(render(roles["overview"], plan["implication_lead"]))
    if plan.get("implication_box"):
        box, slots = fill_box(
            section_xml, BOX_TABLE_INDEX["implication_box"], plan["implication_box"]
        )
        add(box)
        _warn_slots("implication_box", plan["implication_box"], slots)
    add(blank(roles["body"]))

    # --- main body blocks (결과N / 첫째~ / 번호 소제목 -- all paragraph lists) ---
    for block in plan.get("blocks", []):
        add(render(roles["result_title"], block["title"]))
        for para in block.get("paragraphs", []):
            add(render(roles["body"], para))
            add(blank(roles["body"]))
        for table in block.get("tables", []):
            if table.get("caption"):
                add(render(roles["table_caption"], table["caption"]))
            add(build_table(section_xml, table["headers"], table["rows"]))
            add(blank(roles["body"]))
        for note in block.get("notes", []):
            add(render(roles["note"], note))
        add(blank(roles["body"]))

    # --- 기관 입장 / 제언 / 클로징 ---
    for line in plan.get("position", []):
        add(render(roles["position"], line))
    for line in plan.get("proposals", []):
        add(render(roles["position"], line))
    if plan.get("closing"):
        add(render(roles["closing"], plan["closing"]))
    add(blank(roles["publish"]))

    # --- 발행정보 + 문의 (footer is intentionally absent: see SKILL.md) ---
    for line in plan.get("publish", []):
        add(render(roles["publish"], line))

    return out


def _warn_slots(name, lines, slots):
    if len(lines) > slots:
        print(
            f"  warning: {name} has {len(lines)} lines but the reference box holds "
            f"{slots}; the overflow was folded into the last line."
        )
    elif len(lines) < slots:
        print(f"  note: {name} leaves {slots - len(lines)} blank line(s) in the box.")


def build(plan, output_path, reference=REFERENCE):
    doc = read_hwpx.open_hwpx(reference)
    section_name = doc.list_sections()[0]
    section_xml = doc.get_entry_text(section_name)

    roles = discover_roles(section_xml)
    fragments = compose_body(plan, roles, section_xml)
    new_body = "".join(fragments)

    spans = find_top_level_paragraphs(section_xml)
    total = len(spans)

    def modifier(xml):
        # Order matters. Delete the reference's paragraphs 1..N-1 FIRST, back to
        # front so each index is still valid as the list shrinks, leaving only
        # paragraph 0 as an anchor. Only then swap that anchor for the new body.
        #
        # Doing it the other way round silently keeps the original content: the
        # replacement expands paragraph 0 into ~45 paragraphs, every later index
        # shifts by that amount, and the subsequent deletes chew through the new
        # body instead of the old one.
        out = xml
        for idx in range(total - 1, 0, -1):
            out = modify_hwpx.delete_paragraph(out, idx)
        out = modify_hwpx.replace_paragraph(out, 0, new_body)
        return table_fixer.fix_all_tables(out)

    modify_hwpx.update_section(
        str(reference), section_name, modifier, output_path=str(output_path)
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Build a 교육의봄 press release HWPX")
    parser.add_argument("--plan", "-p", required=True, help="Plan JSON path")
    parser.add_argument("--output", "-o", required=True, help="Output .hwpx path")
    parser.add_argument("--reference", "-r", default=str(REFERENCE), help="Style donor .hwpx")
    parser.add_argument(
        "--linesegs",
        choices=("estimate", "single"),
        default="estimate",
        help="Line geometry strategy (default: estimate -- verified in Hancom)",
    )
    args = parser.parse_args()

    global LINESEG_MODE
    LINESEG_MODE = args.linesegs

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    build(plan, Path(args.output), reference=Path(args.reference))
    print(f"Generated: {args.output}")


if __name__ == "__main__":
    main()
