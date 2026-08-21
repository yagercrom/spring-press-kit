# HWPX 저수준 XML 구조 참조

> 이 문서는 HWPX 파일의 내부 구조, 네임스페이스, 페이지 설정 등 저수준 XML 조작이 필요할 때 참조한다.

## 문서 구조

HWPX 파일의 내부 ZIP 구조:

```
document.hwpx (ZIP)
├── mimetype
├── META-INF/
│   ├── container.xml
│   ├── container.rdf
│   └── manifest.xml
├── version.xml
├── settings.xml
├── Preview/
│   ├── PrvImage.png
│   └── PrvText.txt
└── Contents/
    ├── content.hpf        ← 매니페스트 (파트 목록, 이미지 참조)
    ├── header.xml          ← 스타일/글꼴/문단속성/테두리배경 정의
    └── section0.xml        ← 본문 내용 (섹션 추가 시 section1.xml 등)
```

## HWPUNIT 변환

```
1mm ≈ 283.46 HWPUNIT   (7200 HWPUNIT = 1 inch)
```

### 주요 변환표

| 항목 | mm | HWPUNIT |
|------|-----|---------|
| A4 너비 | 210 | 59528 |
| A4 높이 | 297 | 84186 |
| 20mm | 20 | 5669 |
| 15mm | 15 | 4252 |
| 10mm | 10 | 2835 |

## 네임스페이스 매핑

| 네임스페이스 URI | 표준 프리픽스 | 사용 위치 |
|-----------------|-------------|----------|
| `http://www.hancom.co.kr/hwpml/2011/head` | `hh` | header.xml |
| `http://www.hancom.co.kr/hwpml/2011/core` | `hc` | header.xml, section*.xml |
| `http://www.hancom.co.kr/hwpml/2011/paragraph` | `hp` | header.xml, section*.xml |
| `http://www.hancom.co.kr/hwpml/2011/section` | `hs` | section*.xml |
| `http://www.hancom.co.kr/hwpml/2011/app` | `ha` | |
| `http://www.hancom.co.kr/hwpml/2016/paragraph` | `hp10` | 2016 확장 |

## header.xml 주요 요소

### 글꼴 정의 (fontfaces)

글꼴은 `<hh:fontface lang="HANGUL|LATIN|...">` 그룹 내에서 id로 참조:

```xml
<hh:fontface lang="HANGUL" fontCnt="8">
  <hh:font id="0" face="함초롬돋움" type="TTF" isEmbedded="0"/>
  <hh:font id="1" face="함초롬바탕" type="TTF" isEmbedded="0"/>
  <hh:font id="2" face="휴먼명조" type="TTF" isEmbedded="0"/>
  <hh:font id="3" face="HY헤드라인M" type="TTF" isEmbedded="0"/>
  <hh:font id="6" face="한양중고딕" type="HFT" isEmbedded="0"/>
</hh:fontface>
```

### 글자 속성 (charPr)

```xml
<hh:charPr id="5" height="1600" textColor="#000000" ...>
  <hh:fontRef hangul="3" .../>  <!-- hangul="3" → HY헤드라인M -->
  <hh:bold .../>
</hh:charPr>
```

- `height`: 1/100pt 단위 (1600 = 16pt)
- `textColor`: 글자 색상
- `fontRef hangul="N"`: HANGUL fontface 내 id=N 글꼴 참조

### 문단 속성 (paraPr)

```xml
<hh:paraPr id="28">
  <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
  <hh:heading type="NONE" idRef="0" level="0"/>
  <hh:margin><hc:intent value="-2606" unit="HWPUNIT"/></hh:margin>
  <hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>
  <hp:spacing before="0" after="0" .../>
</hh:paraPr>
```

- `horizontal`: JUSTIFY, CENTER, LEFT, RIGHT
- `hc:intent value`: 들여쓰기 (음수 = 내어쓰기)
- `lineSpacing`: 줄간격 (PERCENT=160 → 160%)
- `spacing before/after`: 문단 전/후 간격

### 테두리/배경 (borderFill)

```xml
<hh:borderFill id="9">
  <hh:leftBorder type="SOLID" width="0.12 mm" color="#006699"/>
  <!-- ... 기타 테두리 ... -->
  <hh:fillBrush>
    <hh:windowBrush faceColor="#193AAA" .../>
  </hh:fillBrush>
</hh:borderFill>
```

## section0.xml 주요 요소

### 페이지 설정

```xml
<hp:pagePr landscape="WIDELY" width="59528" height="84188" gutterType="LEFT_ONLY">
  <hp:margin header="4251" footer="4251" gutter="0"
             left="5669" right="5669" top="4251" bottom="4251"/>
</hp:pagePr>
```

### 문단

```xml
<hp:p id="..." paraPrIDRef="28" styleIDRef="0" pageBreak="0">
  <hp:run charPrIDRef="5">
    <hp:t>본문 텍스트</hp:t>
  </hp:run>
</hp:p>
```

- `paraPrIDRef`: header.xml의 paraPr id 참조
- `charPrIDRef`: header.xml의 charPr id 참조
- `pageBreak="1"`: 이 문단 앞에서 페이지 나눔

### 테이블

```xml
<hp:tbl ... rowCnt="1" colCnt="3" borderFillIDRef="5">
  <hp:sz width="47688" widthRelTo="ABSOLUTE" height="2832" .../>
  <hp:pos treatAsChar="1" horzAlign="LEFT" .../>
  <hp:tr>
    <hp:tc borderFillIDRef="9">
      <hp:subList vertAlign="CENTER">
        <hp:p paraPrIDRef="3">
          <hp:run charPrIDRef="24"><hp:t>Ⅰ</hp:t></hp:run>
        </hp:p>
      </hp:subList>
      <hp:cellAddr colAddr="0" rowAddr="0"/>
      <hp:cellSz width="3327" height="2832"/>
    </hp:tc>
    <!-- ... 나머지 셀 ... -->
  </hp:tr>
</hp:tbl>
```

### 이미지 참조

이미지는 3단계로 참조된다:

1. **content.hpf** manifest에 등록:
```xml
<opf:item id="image1" href="BinData/image1.png"
          media-type="image/png" isEmbeded="1"/>
```

2. **BinData/** 폴더에 실제 파일 존재

3. **section0.xml**에서 참조:
```xml
<hc:img binaryItemIDRef="image1" bright="0" contrast="0"
        effect="REAL_PIC" alpha="0"/>
<hp:imgRect>
  <hc:pt0 x="0" y="0"/>
  <hc:pt1 x="8196" y="0"/>
  <hc:pt2 x="8196" y="3382"/>
  <hc:pt3 x="0" y="3382"/>
</hp:imgRect>
```

## 페이지 설정 변경 (코드)

`pagePr` 속성을 DOM으로 고쳐서 저장하면 안 된다 — 재직렬화가 일어나 한글이 파일을 거부한다(SKILL.md 규칙 1). **속성값만 정규식으로 바꾼다.**

```python
import re, sys
sys.path.insert(0, r"<SKILL_DIR>")
from scripts import modify_hwpx

MARGINS = {           # 보고서 기준: 좌우 20mm, 상하 15mm
    "left": "5669", "right": "5669", "top": "4252", "bottom": "4252",
}

def resize(section_xml):
    # A4 용지 크기
    section_xml = re.sub(r'(<hp:pagePr\b[^>]*?\bwidth=")\d+', r"\g<1>59528", section_xml)
    section_xml = re.sub(r'(<hp:pagePr\b[^>]*?\bheight=")\d+', r"\g<1>84186", section_xml)
    # 여백 — hp:margin 태그 안에서만 치환
    def fix_margin(m):
        tag = m.group(0)
        for attr, value in MARGINS.items():
            tag = re.sub(rf'({attr}=")\d+', rf"\g<1>{value}", tag)
        return tag
    return re.sub(r"<hp:margin\b[^>]*/>", fix_margin, section_xml)

modify_hwpx.update_section(
    "document.hwpx", "Contents/section0.xml", resize, output_path="resized.hwpx"
)
```

`update_section()` 이 압축방식 보존과 well-formedness 검증을 함께 처리하므로 별도 후처리는 필요 없다.

## 호환성

- **HWPX ↔ HWP**: 이 스킬은 HWPX만 처리한다. 레거시 바이너리 `.hwp`는 다룰 수 없으므로, 한글에서 `.hwpx`로 저장해 달라고 요청할 것
- **한컴오피스 버전**: HWPX는 2014 이후 지원, 2021년부터 기본 포맷
- **다른 뷰어**: 제한적. 배포 시 PDF 변환 병행 권장
