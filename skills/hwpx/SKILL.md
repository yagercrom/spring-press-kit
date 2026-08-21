---
name: hwpx
description: "한글(HWPX) 문서를 생성·읽기·편집하고 기존 양식에 내용을 채워 넣는 스킬. 'hwpx', 'HWPX', '한글 문서', '한글파일', '한글로 작성', 'HWP', '한컴', 'Hancom', '보고서', '업무보고', '공문', '기안문', '결과보고서', '.hwpx 만들어줘' 같은 말이 나오면 이 스킬을 사용할 것. 사용자가 한국 공공기관·기업 양식의 문서를 원하거나 .hwpx 파일을 첨부했다면 '한글'이라는 단어를 쓰지 않아도 이 스킬을 사용할 것. 파이썬 표준 라이브러리만 사용하므로 추가 설치가 필요 없다. Word(.docx)는 docx 스킬, PDF는 pdf 스킬을 사용할 것."
---

# HWPX 문서 스킬

HWPX는 한컴오피스 한글의 개방형 포맷이다. 실체는 **ZIP 아카이브 + XML 파트**이며 KS X 6101(OWPML) 표준을 따른다.

이 스킬은 **파이썬 표준 라이브러리만** 사용한다. `pip install`이 필요 없고 어떤 환경에서도 바로 동작한다. `python-hwpx`나 `jakal-hwpx` 같은 외부 라이브러리를 설치하지 말 것 — `scripts/`의 모듈이 그 역할을 대체하며, 섞어 쓰면 아래 무결성 규칙이 깨진다.

## 왜 이 스킬이 필요한가

한글은 파일을 매우 엄격하게 검증한다. 문법적으로 올바른 XML을 만들어도 한컴오피스가 "손상된 파일"로 거부하는 경우가 흔하다. 실패 원인은 대개 XML 문법이 아니라 **바이트 수준의 형태**다: 재직렬화로 인한 줄바꿈·속성 순서 변경, ZIP 엔트리 압축방식 변경, 표의 `rowCnt` 불일치. `scripts/`의 모듈들은 그런 실패에서 얻은 규칙을 코드로 고정해 둔 것이다. XML을 직접 조립하기 전에 이 모듈을 먼저 쓸 것.

## 첫 번째 결정: 어떤 경로로 만들 것인가

세 갈래가 있다. 위에서부터 확인한다.

### 1. 사용자가 `.hwpx` 양식을 제공했는가 → 양식 치환

사용자가 자기 양식 파일을 주면서 "이 양식으로", "이 파일 기반으로"라고 하면 **반드시 그 파일을 쓴다.** 기본 양식으로 갈아타지 말 것 — 사용자 양식에는 기관 로고, 결재란, 서식 규정이 이미 들어 있고 그게 요청의 핵심이다.

→ **`references/template-replacement.md`** 를 읽고 그 절차를 따를 것.

### 2. 표준 보고서 양식이 필요한가 → 내장 양식 사용

`assets/`에 성격이 다른 양식 두 개가 있다. 문서 종류에 맞는 쪽을 고른다.

| 양식 | 구성 | 기호 체계 | 방법 |
|---|---|---|---|
| `template.hwpx` | 표지 + 본문 + 참고(부록) | □ / ㅇ / - / * | config JSON 생성 |
| `report-template.hwpx` | 표지 + 목차 + 결재란 + 섹션 바(Ⅰ~Ⅴ) | □ / ○ / ― / ※ | 플레이스홀더 치환 |

- **표지·목차·결재란이 필요한 정식 보고서** → `report-template.hwpx` + 치환 (`references/report-style.md`)
- **그 외 일반 업무보고·결과보고** → `template.hwpx` + config JSON (아래)

### 3. 아주 단순한 메모·목록인가 → config JSON 최소 구성

표지 없이 본문만 필요하면 `include_cover: false`로 생성한다. 다만 보고서·공문처럼 양식이 있는 문서를 빈 문서에서 조립하지 말 것 — 색 배경 셀, 섹션 바, 장식 표 같은 디자인 요소는 처음부터 만들기가 훨씬 어렵고 결과도 나쁘다.

## 생성: config JSON → HWPX

`scripts/`는 파이썬 패키지다(내부에서 상대 임포트를 쓴다). 따라서 **스킬 디렉터리에서 `-m`으로 실행**해야 한다. 스크립트를 파일 경로로 직접 실행하면 `ImportError: attempted relative import with no known parent package`로 죽는다.

```bash
cd "<SKILL_DIR>"
python -m scripts.generate_hwpx --output "<출력경로>.hwpx" --config "<설정>.json"
```

`<SKILL_DIR>`는 이 SKILL.md가 있는 디렉터리다. 다른 양식을 쓰려면 `--template <경로>.hwpx`를 붙인다.

파이썬에서 직접 호출할 때는 스킬 디렉터리를 `sys.path`에 넣는다:

```python
import sys, json
sys.path.insert(0, r"<SKILL_DIR>")
from scripts.generate_hwpx import generate_hwpx

config = json.load(open("config.json", encoding="utf-8"))
generate_hwpx(config, "output.hwpx")
```

### config JSON 구조

```json
{
  "title": "보고서 제목",
  "subtitle": "부제목 (생략 가능)",
  "date": "2026. 2. 14.",
  "department": "담당부서",
  "include_cover": true,
  "sections": [
    {
      "type": "body",
      "title_bar": "본문 제목",
      "content": [
        {"type": "heading",   "text": "대분류 항목"},
        {"type": "bullet",    "text": "중분류 항목"},
        {"type": "dash",      "text": "세부 항목"},
        {"type": "star",      "text": "참고·주석"},
        {"type": "paragraph", "text": "기호 없는 본문"},
        {"type": "note",      "text": "참고 내용"},
        {"type": "table", "caption": "표 제목",
         "headers": ["항목", "내용", "비고"],
         "rows": [["데이터1", "설명1", "비고1"]]}
      ]
    },
    {
      "type": "appendix",
      "title_bar": "참고1",
      "appendix_title": "부록 제목",
      "content": []
    }
  ]
}
```

`examples/sample_report.json`과 `examples/long_report.json`에 동작하는 예시가 있다. 새 config를 쓸 때 먼저 열어 볼 것.

### 계층 기호를 올바르게 쓰는 법

`heading`(□) → `bullet`(ㅇ) → `dash`(-) → `star`(*)는 **의미적 계층**이다. 보기 좋게 만들려고 단계를 건너뛰지 말 것. 한국 공공기관 보고서를 읽는 사람은 이 기호로 논리 구조를 파악하므로, `heading` 없이 `dash`만 나열하면 무엇이 상위 주장인지 알 수 없다.

| 타입 | 기호 | 글꼴 | 크기 |
|---|---|---|---|
| `heading` | □ | HY헤드라인M | 15pt |
| `bullet` | ㅇ | 휴먼명조 | 15pt |
| `dash` | - | 휴먼명조 | 15pt |
| `star` | * | 맑은고딕 | 13pt |
| `paragraph` | (없음) | 휴먼명조 | 15pt |
| `table` | (표) | 맑은고딕 | 12pt |

## 읽기와 수정: 기존 파일 다루기

원칙은 하나다. **분석은 파서로, 수정은 원본 바이트에.**

두 단계는 API 모양이 다르다. 읽기는 문서 객체를 열어 메서드를 부르고, 수정은 섹션 XML 문자열을 받아 새 문자열을 돌려주는 순수 함수들이다. 이 구분이 있는 이유는 규칙 1 때문이다 — 수정 함수가 문서 객체를 들고 있으면 무심코 재직렬화해서 저장하기 쉬운데, 문자열만 주고받으면 그럴 수 없다.

### 읽기: `open_hwpx()` 로 객체를 얻고 메서드 호출

```python
import sys
sys.path.insert(0, r"<SKILL_DIR>")
from scripts import read_hwpx

doc = read_hwpx.open_hwpx("input.hwpx")
print(doc.get_structure_summary())     # 섹션·표·이미지·스타일 개수
print(doc.list_sections())             # ['Contents/section0.xml', ...]
print(doc.list_tables())               # 섹션별 rowCnt/colCnt/headers/위치
print(doc.get_styles())                # charPr/paraPr/borderFill/font 카탈로그
print(doc.list_paragraphs("Contents/section0.xml"))
print(doc.list_images())
section_xml = doc.get_entry_text("Contents/section0.xml")   # str
```

`get_structure_summary()` 등은 **인스턴스 메서드**다. `read_hwpx.get_structure_summary(path)` 처럼 모듈 함수로 부르면 `AttributeError` 가 난다.

### 수정: 섹션 XML 문자열을 변환하는 함수들

`modify_hwpx`·`table_fixer`·`xml_templates` 의 함수들은 **`str` 을 받아 `str` 을 돌려준다.** 매개변수 이름이 `section_bytes` 이지만 실제로는 문자열이 필요하다 — `doc.get_entry_bytes()` 를 넘기면 `TypeError` 가 난다. `get_entry_text()` 를 쓸 것.

| 하려는 일 | 함수 |
|---|---|
| 텍스트 치환 (`max_count=N` 으로 앞 N개만) | `modify_hwpx.replace_text(xml, old, new, max_count=0)` |
| 표 특정 셀 텍스트 치환 | `modify_hwpx.replace_text_in_cell(xml, row_addr, col_addr, new_text)` |
| 문단 삽입·삭제·교체 | `insert_paragraph_after(xml, anchor_index, para_xml)`, `delete_paragraph(xml, para_index)`, `replace_paragraph(...)` |
| 표 행 삽입·삭제 | `insert_table_row(xml, table_index, row_xml, position=-1)`, `delete_table_row(xml, table_index, row_index)` |
| well-formedness 검증 | `modify_hwpx.validate_output(xml)` |
| 표 정합성 검증·수정 | `table_fixer.validate_all_tables(xml)`, `fix_all_tables(xml)` |
| 기존 문단·표를 템플릿으로 추출 | `xml_templates.extract_paragraph_by_pattern(xml, text_pattern)`, `extract_table_template(xml, table_index)` |
| 템플릿에 값 주입 | `xml_templates.render_paragraph(tpl, text, ...)`, `render_table(tpl, headers, rows)` |
| 닫히지 않은 CDATA·주석 탐지 | `_parser.check_for_unclosed_constructs(xml)` |

문단·표를 **인덱스**로 지정한다는 점에 주의할 것. 패턴 문자열이 아니다. 인덱스는 `doc.list_paragraphs()` / `doc.list_tables()` 결과에서 얻는다.

### 파일 단위로 적용: `update_section()`

섹션 문자열을 고친 뒤 ZIP으로 되돌리는 것까지 한 번에 처리한다. 압축방식 보존(규칙 3)과 검증(규칙 4)이 안에 들어 있다.

```python
from scripts import modify_hwpx, table_fixer

def fix(section_xml):
    section_xml = modify_hwpx.replace_text(section_xml, "기존 제목", "새 제목")
    return table_fixer.fix_all_tables(section_xml)

modify_hwpx.update_section(
    "input.hwpx", "Contents/section0.xml", fix, output_path="output.hwpx"
)
```

여러 섹션을 한꺼번에 고칠 때는 `update_sections(path, {섹션명: 함수, ...}, output_path)` 를 쓴다. ZIP 엔트리를 직접 갈아 끼워야 하면 `zip_handler.replace_entry(path, entry_name, new_data, output_path)` 가 있다.

## 무결성 규칙 — 어기면 한글이 파일을 거부한다

아래 다섯 가지는 실제 실패에서 나온 것이다. 이유를 알고 지킬 것.

1. **최종 출력에 `etree.tostring()`을 쓰지 말 것.** 원본 HWPX XML은 한 줄 compact 포맷이다. 재직렬화하면 pretty-print와 속성 재정렬이 일어나고, 한컴오피스는 그 차이를 변조로 판정한다. `etree.parse()`는 **읽기 분석 전용**이고, 수정은 `str.replace()`나 정규식으로 원본 바이트에 직접 한다. `modify_hwpx.py`가 이미 그 방식이니 그걸 쓰면 된다.

2. **표를 고쳤으면 `rowCnt`·`cellAddr`·`rowAddr`를 다시 맞출 것.** `<hp:tbl>`의 `rowCnt`가 실제 `<hp:tr>` 개수와 다르면 파일 열기 자체가 실패한다. 셀 병합(colSpan/rowSpan)이 있으면 논리적 그리드 위치를 계산해야 하는데 `table_fixer.fix_all_tables()`가 자동 처리한다. 손으로 세지 말 것.

3. **ZIP 엔트리별 압축방식을 보존할 것.** `mimetype`은 반드시 첫 엔트리이고 `ZIP_STORED`(무압축)여야 한다. 나머지도 원본의 `compress_type`을 유지한다. `zip_handler.py`가 원본 메타데이터를 기록해 두고 재패키징 때 되돌려 준다. `zipfile.ZipFile`로 직접 다시 쓰면 이 정보가 날아간다.

4. **문자열 수술 후 well-formedness를 검증할 것.** 삽입 위치가 어긋나면 XML이 깨지는데, 같은 파서로만 검증하면 같은 버그를 공유해 발견되지 않는다. `update_section()`은 기본값 `validate=True`로 수정 전후를 `ET.fromstring()`으로 검사한다(읽기 전용 검증이며 `tostring()`은 쓰지 않는다). 끄지 말 것.

5. **닫히지 않은 CDATA·주석을 경계할 것.** 손상된 입력에서 `<![CDATA[`가 닫히지 않으면 파서가 내부 문자열을 실제 태그로 오인해 유령 요소를 만든다. 의심되면 파싱 전에 `check_for_unclosed_constructs(xml)`로 확인한다. 빈 리스트면 안전하다.

## 문서 종류별 규격

문서를 쓰기 전에 해당 레퍼런스를 먼저 읽을 것. 보고서와 공문서는 **기호 체계·글꼴·여백이 전부 다르다.** 섞으면 받는 사람이 바로 알아본다.

| 상황 | 읽을 것 |
|---|---|
| 공문서·기안문 (수신/제목/붙임, `1. 가. 1)` 체계) | `references/official-doc-style.md` |
| 내부 보고서 (표지·목차·결재란, `□○―※` 체계) | `references/report-style.md` |
| 사용자 제공 양식에 내용 채우기 | `references/template-replacement.md` |
| 저수준 XML을 직접 다뤄야 할 때 | `references/xml-internals.md` |

`official-doc-style.md`는 「행정업무의 운영 및 혁신에 관한 규정」과 시행규칙을 근거로 정리한 것이다. 날짜 표기(`2026. 2. 13.`), 항목 기호 8단계, "끝" 표시, 붙임 규칙 같은 것은 관행이 아니라 규정이므로 임의로 바꾸지 말 것.

## 자주 나오는 함정

- **날짜 형식**: 공문서는 `2026-02-13`이 아니라 `2026. 2. 13.`이다. 월·일 앞에 `0`을 붙이지 않고 끝에 온점을 찍는다.
- **글꼴 임베딩 없음**: 생성된 HWPX에 글꼴은 포함되지 않는다. HY헤드라인M·휴먼명조가 없는 PC에서는 다르게 보인다. 배포용이면 PDF 변환을 함께 제안할 것.
- **레이아웃 엔진이 아니다**: 페이지 나눔과 줄 넘김은 한글 앱이 열 때 결정한다. "정확히 3페이지" 같은 요구는 생성 단계에서 보장할 수 없다.
- **`.hwp`는 다른 포맷이다**: 레거시 바이너리 `.hwp`는 이 스킬로 처리할 수 없다. 사용자가 `.hwp`를 줬다면 한글에서 `.hwpx`로 저장해 달라고 요청할 것.
- **표 캡션 위치**: `table`의 `caption`은 표 위에 붙는다. 한국 공문서 관행상 표 제목은 위, 출처·주석은 아래(`star`)다.

## 결과 전달과 검증

이 스킬은 로컬 파일 시스템 기준으로 동작한다. 출력 경로는 사용자가 지정한 곳이나 현재 작업 디렉터리를 쓰고, 샌드박스 전용 경로(`/mnt/user-data/outputs` 등)를 가정하지 말 것.

생성 직후 검증을 한 번 돌리면 조용한 실패를 막을 수 있다. 표를 넣었는데 표 수가 0이거나 섹션 수가 config와 다르면 생성이 조용히 실패한 것이다.

```python
import sys, zipfile
sys.path.insert(0, r"<SKILL_DIR>")
from scripts import read_hwpx, table_fixer

doc = read_hwpx.open_hwpx("output.hwpx")
print(doc.get_structure_summary())          # 섹션·표 수가 config와 맞는가
for name in doc.list_sections():            # 표 정합성 (규칙 2)
    errs = table_fixer.validate_all_tables(doc.get_entry_text(name))
    print(name, len(errs), "error(s)")

with zipfile.ZipFile("output.hwpx") as z:   # ZIP 불변식 (규칙 3)
    first = z.infolist()[0]
    assert first.filename == "mimetype"
    assert first.compress_type == zipfile.ZIP_STORED
    assert z.testzip() is None
```

확인 후 파일 경로를 사용자에게 알리고, 파일을 보여줄 수 있는 도구가 있으면 그것으로 전달한다.
