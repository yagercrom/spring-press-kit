# 교육의봄 보도자료 스킬 (spring-press-kit)

Claude Code에서 교육의봄 보도자료를 기관 서식 그대로 HWPX로 만들어 주는 스킬 묶음입니다.

## 무엇이 들어 있나

| 스킬 | 역할 |
|---|---|
| `spring_press_contents_maker_1.0` | 보도자료 작성 + 기관 서식 HWPX 생성 |
| `hwpx` | 한글(HWPX) 문서 생성·읽기·편집 |

**두 스킬은 함께 설치해야 합니다.** 보도자료 스킬이 HWPX 처리를 전부 `hwpx` 스킬에서 가져오므로, 하나만 설치하면 동작하지 않습니다.

## 필요한 것

- **Claude Code**
- **Python 3.9 이상** — 생성기가 파이썬으로 동작합니다. `pip install`은 필요 없습니다(표준 라이브러리만 사용)
- 결과를 확인·수정하려면 **한글(한컴오피스)**

## 설치 방법 A — ZIP (권장, 가장 간단)

압축을 풀고 그 폴더에서:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

`~/.claude/skills/` 에 두 스킬을 복사하고, 생성 테스트까지 돌려 설치가 정상인지 확인합니다.

먼저 무엇이 바뀔지만 보고 싶으면:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1 -WhatIf
```

같은 이름의 스킬이 이미 있으면 **덮어쓰기 전에 `~/.claude/backups/` 로 백업**합니다.

설치 후 **Claude Code를 재시작**하세요. 스킬은 세션 시작 시 로드됩니다.

## 설치 방법 B — 플러그인 마켓플레이스

이 폴더를 Git 저장소로 올리면 그 자체가 마켓플레이스가 됩니다(`.claude-plugin/marketplace.json` 포함). 팀원은 두 줄로 설치합니다.

```bash
claude plugin marketplace add <조직>/<저장소>
```

```bash
claude plugin install spring-press-kit@spring
```

업데이트는 `claude plugin update spring-press-kit`. ZIP을 다시 배포할 필요가 없어 관리가 편합니다.

> 이 저장소는 공개(public)입니다. 서식 공급원인 `assets/press-release-reference.hwpx` 는 이미 언론에 배포된 보도자료이고, 미발표 자료와 내부 지침 원본은 배포본에서 제외했습니다. 새 예시를 추가할 때 **발표 전 수치나 실명이 들어가지 않도록** 주의하세요 — `examples/` 의 두 파일은 구조를 보여주기 위한 가상 사례입니다.

## 쓰는 방법

재시작 후 그냥 요청하면 됩니다.

```
이 분석 보고서로 보도자료 초안 써줘
```

자료(설문 원데이터, 회견문, 분석 보고서 등)를 함께 주면 그것을 읽고 작성합니다. 스킬이 하는 일:

1. 보도자료 **유형 판별** (A 조사·설문 발표형 / B 회견·성명형 / C 이슈 심층형)
2. 유형별 구조·기호·문체 적용
3. **plan JSON** 작성
4. 기관 서식 **HWPX 생성**
5. **검증** (표 정합성, 원본 문장 잔여, ZIP 무결성)

### 수정할 때

생성된 HWPX를 직접 고치기보다 **plan JSON을 고쳐 다시 생성**하는 편이 안전합니다.

```bash
python "%USERPROFILE%\.claude\skills\spring_press_contents_maker_1.0\tools\build_press_release.py" --plan plan.json --output 보도자료.hwpx
```

```bash
python "%USERPROFILE%\.claude\skills\spring_press_contents_maker_1.0\tools\verify.py" 보도자료.hwpx
```

`examples/` 에 동작하는 plan JSON 두 개가 있습니다. 새로 쓸 때 복사해서 고치면 빠릅니다.

## 알아둘 점

- **서식은 실제 발행본을 복제합니다.** 모든 문단이 `assets/press-release-reference.hwpx` 의 문단을 복제해 텍스트만 바꾼 것이라 글꼴·자간·줄간격·박스 테두리가 원본과 같습니다.
- **개요·결과요약·시사점 박스는 줄 수가 고정**입니다. 내용이 넘치면 경고가 나오니 줄이거나 본문으로 옮기세요.
- **기관정보 푸터는 넣지 않습니다.** 실제 발행본에 없고, 대표 이메일이 확정되지 않았습니다.
- **글꼴은 파일에 포함되지 않습니다.** HY헤드라인M·휴먼명조가 없는 PC에서는 다르게 보입니다. 외부 배포용이면 PDF를 함께 만드세요.
- **수치는 확인하고 쓰세요.** 스킬은 준 자료를 그대로 옮기지만, 원자료 안에 서로 어긋나는 수치가 있으면 그것까지는 대신 판단하지 못합니다. 보도자료에서 가장 치명적인 실수라 생성 후 눈으로 한 번 보는 것을 권합니다.

## 문제가 생기면

| 증상 | 원인·조치 |
|---|---|
| `hwpx skill not found` | `hwpx` 스킬이 없습니다. 두 스킬을 함께 설치하세요. |
| 스킬이 안 잡힌다 | Claude Code를 완전히 종료하고 다시 실행하세요. |
| 자간·줄간격이 흐트러진다 | `--linesegs estimate`(기본값)인지 확인하세요. `single`은 한글에서 어긋납니다. |
| 표 캡션이 겹쳐 나온다 | 구버전 증상입니다. 1.0 이상인지 확인하세요. |
| `verify.py` 가 FAIL | 출력에 실패 항목이 나옵니다. 표 정합성 오류면 plan의 `headers`·`rows` 열 수를 맞추세요. |
