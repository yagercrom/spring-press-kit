# 양식 채우기 (템플릿 치환)

기존 `.hwpx` 양식에 내용을 채워 넣는 절차. 사용자가 자기 양식을 제공한 경우와 내장 `report-template.hwpx` 를 쓰는 경우 모두 같다.

## 왜 새로 만들지 않고 채우는가

양식에는 기관 로고(BinData), 결재란, 색 배경 셀, 섹션 구분 바, 여백·글꼴 규정이 이미 들어 있다. 이런 요소는 `header.xml` 의 `borderFill`·`charPr` 정의와 얽혀 있어서 처음부터 재현하려면 정의를 함께 만들어야 하고, 결과물도 원본과 미묘하게 달라진다. 텍스트만 갈아 끼우면 그 전부가 그대로 보존된다.

## 절차

### 1단계: 원본을 건드리지 말고 복사한다

```python
import shutil
shutil.copy(TEMPLATE_PATH, WORK_PATH)
```

양식 파일은 재사용 자산이다. 제자리에서 수정하면 두 번째 문서를 만들 때 플레이스홀더가 이미 사라져 있다.

### 2단계: 텍스트를 전수 조사한다 — 건너뛰지 말 것

```bash
cd "<SKILL_DIR>"
python -m scripts.inspect_template "<양식>.hwpx"
python -m scripts.inspect_template "<양식>.hwpx" --repeated-only
```

이 단계를 건너뛰고 플레이스홀더 문자열을 추측하면 **조용히 실패한다.** `replace_text()` 는 찾지 못해도 예외를 던지지 않고 원본을 그대로 돌려주며, 파일은 정상적으로 열린다. 결과적으로 플레이스홀더가 그대로 박힌 문서가 사용자에게 전달된다.

출력에서 세 가지를 확인한다.

- **고유 문자열**: 한 번만 나오므로 그냥 치환하면 된다.
- **반복 문자열** (`[3/8]` 처럼 표시됨): 같은 문자열이 여러 번 나온다. 한 번의 `replace_text()` 로는 전부 같은 값이 되므로 순차 치환이 필요하다(4단계).
- **중첩 마크업 경고**: 값 안에 `<hp:tab>` 같은 태그가 들어 있는 항목. 통째로 치환하면 그 요소가 파괴된다.

### 3단계: 치환 매핑을 만든다

조사 결과를 보고 "어떤 문자열을 무엇으로" 표를 만든다. 양식마다 플레이스홀더가 다르므로 이 표는 매번 새로 만든다. 내장 `report-template.hwpx` 의 실측 결과는 `report-style.md` 에 정리돼 있다.

### 4단계: 치환한다

`modify_hwpx` 함수들은 섹션 XML **문자열**을 받아 문자열을 돌려준다. 파일 단위 적용은 `update_section()` 이 처리한다 — 압축방식 보존과 well-formedness 검증이 그 안에 들어 있다.

```python
import sys
sys.path.insert(0, r"<SKILL_DIR>")
from scripts import modify_hwpx, table_fixer

ONCE = {
    "브라더 공기관": "○○○정책실",
    "기본 보고서 양식": "2026년 AI 활용 현황 보고",
    "2024. 5. 23.": "2026. 2. 14.",
    "제 목": "AI 활용 현황 및 개선 방안",
}

# 반복 플레이스홀더: 앞에서부터 하나씩 다른 값으로
SEQUENTIAL = [
    ("헤드라인M 폰트 16포인트(문단 위 15)", ["첫 번째 대분류", "두 번째 대분류"]),
    ("  ○ 휴면명조 15포인트(문단위 10)", ["  ○ 첫 번째 중분류", "  ○ 두 번째 중분류"]),
]

def fill(section_xml):
    for old, new in ONCE.items():
        section_xml = modify_hwpx.replace_text(section_xml, old, new)
    for old, values in SEQUENTIAL:
        for value in values:
            # max_count=1 이 핵심: 남은 첫 항목만 바꾸고 나머지는 남겨 둔다
            section_xml = modify_hwpx.replace_text(section_xml, old, value, max_count=1)
    return table_fixer.fix_all_tables(section_xml)

modify_hwpx.update_section(
    WORK_PATH, "Contents/section0.xml", fill, output_path=OUTPUT_PATH
)
```

`max_count=1` 을 빼면 첫 호출에서 8개가 모두 같은 값이 되고, 이후 호출은 바꿀 것을 찾지 못해 아무 일도 하지 않는다. 반복 플레이스홀더에서 가장 흔한 실수다.

### 5단계: 남은 플레이스홀더가 없는지 확인한다

```bash
python -m scripts.inspect_template "<결과>.hwpx"
```

원래의 플레이스홀더 문자열이 하나라도 남아 있으면 3단계 매핑이 불완전한 것이다. 사용자에게 전달하기 전에 반드시 이 확인을 거칠 것 — 2단계에서 말한 조용한 실패가 여기서 걸린다.

## 함정

**섹션 이름을 확인할 것.** 양식이 몇 개 섹션으로 나뉘어 있는지는 양식마다 다르다. 내장 `report-template.hwpx` 는 표지·목차·본문이 모두 `Contents/section0.xml` 한 곳에 있다. 여러 섹션에 걸쳐 있으면 `update_sections(path, {섹션명: 함수, ...}, output_path)` 를 쓴다. 섹션 목록은 `read_hwpx.open_hwpx(path).list_sections()` 로 얻는다.

**기호와 본문이 분리된 경우가 있다.** `report-template.hwpx` 에서 `' □ '` 는 본문과 별개의 텍스트 노드로 8회 나온다(□ 항목이 두 개의 run으로 구성되기 때문). 본문 문자열만 치환하면 되고 `' □ '` 는 건드리지 않는다. 이걸 치환 대상에 넣으면 기호가 사라진다.

**중첩 요소를 품은 노드는 부분만 치환한다.** 목차 항목은 `'. 개요<hp:tab .../> 1'` 처럼 탭 요소를 품고 있다. `'. 개요'` 만 치환하고 `<hp:tab>` 이후는 손대지 않는다. 값 전체를 새 문자열로 바꾸면 점선 리더와 페이지 번호가 사라진다.

**항목 수가 양식보다 많으면 문단을 복제해야 한다.** 양식의 □ 자리가 8개인데 내용이 12개라면, 치환만으로는 4개를 넣을 곳이 없다. 이때는 `xml_templates.extract_paragraph_by_pattern()` 으로 기존 문단을 템플릿으로 뽑고, `render_paragraph()` 로 새 문단을 만들어 `modify_hwpx.insert_paragraph_after(xml, anchor_index, para_xml)` 로 넣는다. 문단은 **인덱스**로 지정하며 인덱스는 `doc.list_paragraphs(section_name)` 에서 얻는다.

**반대로 항목이 적으면 남은 자리를 지운다.** 채우지 않은 플레이스홀더를 그대로 두면 안 된다. `delete_paragraph(xml, para_index)` 로 제거하되, 인덱스가 앞에서부터 밀리므로 **뒤에서부터 삭제**한다.

**표를 손댔으면 정합성을 다시 맞춘다.** 행을 추가·삭제했으면 `table_fixer.fix_all_tables()` 를 마지막에 호출한다. `rowCnt` 가 실제 행 수와 다르면 한글이 파일 열기를 거부한다.
