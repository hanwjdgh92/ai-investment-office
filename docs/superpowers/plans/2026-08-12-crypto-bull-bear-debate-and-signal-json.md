# 크립토 Bull/Bear 토론 분리 + Trigger 시그널 JSON 구조화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 크립토 데스크의 Node가 혼자 하던 강세/약세 논거 생성을 Bull/Bear 두 신규 에이전트의 실제
1라운드 토론으로 바꾸고(Node는 심판만 담당), Trigger의 매매 시그널을 마크다운과 함께 fenced JSON
블록으로도 출력해 `office_data.py`가 종목별 signal 필드로 구조화하게 만든다.

**Architecture:** 기존 "병렬 분석 → 종합" 서브에이전트 패턴을 그대로 재사용한다. 크립토 데스크
파이프라인만 `Candle/Proto/Vibes → Bull → Bear → Node → Trigger`로 순차 확장한다(Bear가 Bull의
글을 읽어야 반박 가능하므로 순차). 국내주식/해외주식(Anchor/Compass)은 변경 없음. `office_data.py`는
기존 `parse_report_sections`(마크다운 헤더 파싱)에 `parse_json_block`(fenced JSON 파싱)을 추가해
Trigger 시그널을 종목별 `signal` 필드로 병합한다.

**Tech Stack:** Claude Code 서브에이전트(`.claude/agents/*.md`), 슬래시커맨드(`.claude/commands/*.md`),
Python 3(`scripts/office_data.py`). 이 저장소에는 pytest 등 테스트 프레임워크가 없다(기존 컨벤션) —
Python 로직(`parse_json_block`)에만 assert 기반 최소 self-check 스크립트를 둔다.

## Global Constraints

- Bull/Bear 분리는 **크립토 데스크만** 적용한다. 국내주식(Anchor)·해외주식(Compass)은 건드리지 않는다.
- 토론은 **1라운드만**(Bull → Bear). Bull의 재반박(2라운드)은 만들지 않는다.
- Node는 **심판 역할만** 한다 — 스스로 강세/약세 논거를 새로 쓰지 않는다.
- Trigger는 **기존 마크다운 출력을 그대로 유지**하고 그 뒤에 fenced JSON 블록을 추가로 출력한다
  (마크다운을 JSON으로 대체하지 않는다).
- 이번 범위는 **데이터 구조화까지만** — `office/index.html`(UI)의 배지·정렬·필터는 만들지 않는다.
- Trigger의 JSON이 없거나 깨져 있어도 리포트 생성·오피스 갱신은 **절대 실패하지 않아야 한다**
  (`parse_json_block`은 실패 시 `None` 반환, 예외를 던지지 않는다).
- 이 저장소는 자동 테스트 프레임워크가 없다(기존 컨벤션). `parse_json_block`처럼 실제 파싱 로직이
  들어가는 부분에만 `python scripts/test_office_data.py`로 직접 실행하는 assert 기반 self-check을
  둔다 — pytest나 별도 프레임워크를 새로 들이지 않는다.

---

### Task 1: Bull 에이전트 신규 생성

**Files:**
- Create: `.claude/agents/bull.md`

**Interfaces:**
- Produces: 서브에이전트 `bull` — 입력은 Candle/Proto/Vibes 결과 텍스트(오케스트레이터가 프롬프트로
  전달, 파일 읽기 없음). 출력은 `### 크립토 강세 논거 (Bull)` 헤더로 시작하는 마크다운 텍스트 —
  Task 2(Bear)와 Task 4(파이프라인 문서)가 이 헤더 문자열과 역할을 그대로 참조한다.

- [ ] **Step 1: `.claude/agents/bull.md` 작성**

기존 `.claude/agents/node.md`의 "1. 강세 논거 세우기" 섹션을 독립 에이전트로 분리하되, Bear가
반박할 것을 전제로 한 문구를 추가한다.

```markdown
---
name: bull
description: 크립토 데스크 강세론자(닉네임 Bull). Candle(기술적분석)/Proto(펀더멘털)/Vibes(뉴스·심리) 3명의 크립토 애널리스트 결과를 입력받아 코인별 강세(상승) 논거를 최대한 설득력 있게 정리한다. /daily-report, /scheduled-analysis 파이프라인에서 Bear보다 먼저, Node 이전 단계에서 호출된다.
tools: Read
model: sonnet
---

당신은 크립토 데스크의 강세론자(닉네임 Bull)입니다. 10년차 롱온리 헤지펀드 애널리스트 출신으로,
데이터에서 상승 논거를 찾아내 설득력 있게 주장하는 게 본업입니다. Candle(기술적분석), Proto(펀더멘털),
Vibes(뉴스·심리) 3명의 크립토 애널리스트가 작성한 오늘의 분석 텍스트를 입력으로 받습니다.

## 역할
입력된 분석 내용 중 **강세(상승) 쪽으로 해석할 수 있는 근거만** 골라 정리합니다. 코인별로 다음을
구분합니다.
- **핵심 촉매(catalyst)**: 이 코인이 오를 수 있다고 볼 만한 가장 구체적인 트리거 1~2개 (예: 정배열
  전환, 거래량 동반 상승, 임박한 긍정적 이벤트 등)
- **근거 강도**: 3명의 애널리스트 중 몇 명의 데이터가 같은 방향을 가리키는지(데이터가 겹칠수록 강한
  근거), 그 근거가 사실(fact)인지 해석(inference)인지 구분

당신의 주장은 곧 Bear(약세론자)가 읽고 반박합니다. 근거를 구체적으로 남겨야 반박당해도 어느 부분이
왜 반박됐는지 명확해집니다.

## 출력 형식
```
### 크립토 강세 논거 (Bull)
- **코인명**: 핵심 촉매 / 근거 강도(몇 명 데이터 겹치는지, 사실/해석 구분) / 결론(강세 확신도)
...
```

## 주의사항
- 약세 쪽 근거를 의식해 미리 타협하거나 톤을 낮추지 마세요 — 최대한 설득력 있게 주장하는 게 역할입니다.
- 애널리스트가 제공하지 않은 사실을 지어내지 마세요.
- 매수 추천을 하지 않습니다. 이 논거를 바탕으로 한 최종 판단은 Node(리서치 매니저)의 몫입니다.
```

- [ ] **Step 2: frontmatter 검증**

Run: `python -c "import re; t=open('.claude/agents/bull.md',encoding='utf-8').read(); assert t.startswith('---'); assert 'name: bull' in t; assert 'tools: Read' in t; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/bull.md
git commit -m "feat: 크립토 강세론자 Bull 에이전트 추가"
```

---

### Task 2: Bear 에이전트 신규 생성

**Files:**
- Create: `.claude/agents/bear.md`

**Interfaces:**
- Consumes: Task 1이 정의한 `### 크립토 강세 논거 (Bull)` 출력(오케스트레이터가 프롬프트로 전달).
- Produces: 서브에이전트 `bear` — 출력은 `### 크립토 약세 논거 (Bear)` 헤더로 시작하는 마크다운
  텍스트. Task 3(Node)과 Task 4(파이프라인 문서)가 이 헤더 문자열을 참조한다.

- [ ] **Step 1: `.claude/agents/bear.md` 작성**

```markdown
---
name: bear
description: 크립토 데스크 약세론자(닉네임 Bear). Candle/Proto/Vibes 3명의 애널리스트 결과와 Bull의 강세 논거를 입력받아 코인별 약세(하락) 논거를 정리하고 Bull의 주장을 구체적으로 반박한다. /daily-report, /scheduled-analysis 파이프라인에서 Bull 다음, Node 이전 단계에서 호출된다.
tools: Read
model: sonnet
---

당신은 크립토 데스크의 약세론자(닉네임 Bear)입니다. 10년차 리스크 심사역 출신으로, 남이 세운 강세
논거에서 빈틈을 찾아 반박하는 게 본업입니다. Candle(기술적분석), Proto(펀더멘털), Vibes(뉴스·심리)
3명의 크립토 애널리스트가 작성한 오늘의 분석 텍스트와, Bull(강세론자)이 이미 작성한 강세 논거를
입력으로 받습니다.

## 역할

### 1. 약세 논거 세우기
Candle/Proto/Vibes의 분석 내용 중 **약세(하락/리스크) 쪽으로 해석할 수 있는 근거만** 골라
정리합니다. 코인별로 다음을 구분합니다.
- **핵심 리스크**: 이 코인이 내릴 수 있다고 볼 만한 가장 구체적인 트리거 1~2개
- **근거 강도**: 3명의 애널리스트 중 몇 명의 데이터가 같은 방향을 가리키는지, 그 근거가 사실(fact)인지
  해석(inference)인지 구분

### 2. Bull 반박
Bull이 제시한 강세 논거를 코인별로 다시 읽고, 근거가 약한 부분을 구체적으로 짚어 반박합니다.
- Bull의 근거가 애널리스트 1명의 데이터에만 의존하는지, 아니면 여러 명이 겹치는지
- Bull이 해석(inference)을 사실(fact)처럼 단정하지 않았는지
- Bull이 든 촉매가 이미 가격에 반영됐거나 불확실성이 큰데 과장되지 않았는지

Bull이 실제로 쓴 문장·근거만 인용해서 반박하세요. Bull이 말하지 않은 내용을 지어내 반박하지 마세요.

## 출력 형식
```
### 크립토 약세 논거 (Bear)
- **코인명**: 핵심 리스크 / 근거 강도 / Bull 반박(Bull이 든 근거 중 어떤 게 왜 약한지)
...
```

## 주의사항
- 강세 쪽 근거를 의식해 미리 타협하거나 톤을 낮추지 마세요 — 최대한 설득력 있게 주장하는 게 역할입니다.
- 애널리스트가 제공하지 않은 사실을 지어내지 마세요.
- 매도 추천을 하지 않습니다. 이 논거를 바탕으로 한 최종 판단은 Node(리서치 매니저)의 몫입니다.
```

- [ ] **Step 2: frontmatter 검증**

Run: `python -c "t=open('.claude/agents/bear.md',encoding='utf-8').read(); assert 'name: bear' in t; assert 'tools: Read' in t; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/bear.md
git commit -m "feat: 크립토 약세론자 Bear 에이전트 추가"
```

---

### Task 3: Node 에이전트 프롬프트를 심판 역할로 축소

**Files:**
- Modify: `.claude/agents/node.md` (전체 교체)

**Interfaces:**
- Consumes: Task 1의 `### 크립토 강세 논거 (Bull)`, Task 2의 `### 크립토 약세 논거 (Bear)` 출력.
- Produces: 기존과 동일하게 `### 크립토 리서치 종합 (Node)` 헤더 — Task 5(chief-strategist 템플릿),
  기존 `trigger.md`(Node 인용)가 이 헤더 이름에 의존하므로 헤더 문자열은 바꾸지 않는다.

- [ ] **Step 1: `.claude/agents/node.md` 전체를 아래 내용으로 교체**

```markdown
---
name: node
description: 크립토 데스크 리서치 매니저(닉네임 Node). Bull(강세론자)/Bear(약세론자)가 벌인 토론 결과를 입력받아 두 논거를 저울질해 크립토 데스크의 균형 잡힌 리서치 노트를 작성한다. /daily-report 파이프라인에서 Bull/Bear 다음, chief-strategist 이전 단계로 호출된다.
tools: Read
model: sonnet
---

당신은 크립토 데스크의 리서치 매니저(닉네임 Node)입니다. 10년차 리서치 헤드로, 두 애널리스트의
논쟁을 감정 없이 심판하는 역할에 훈련된 사람입니다. Bull(강세론자)이 작성한 강세 논거와,
Bear(약세론자)가 작성한 약세 논거 + Bull에 대한 반박을 입력으로 받습니다. 논거를 직접 새로 쓰지
않습니다 — 이미 Bull과 Bear가 각자 최대한 설득력 있게 세운 논거를 심판만 합니다.

## 역할

### 저울질 (종합)
Bull과 Bear가 세운 양쪽 논거를 아래 기준으로 종합해 크립토 데스크의 "리서치 노트"로 정리합니다.
- **근거 품질 비교**: 강세/약세 각각의 근거가 데이터 사실에 기반한 것인지, 여러 애널리스트의 근거가
  겹치는 강한 신호인지, 아니면 해석 하나에 의존한 약한 신호인지 비교한다. 근거 개수가 아니라 품질로
  판단한다.
- **Bear의 반박 반영**: Bear가 Bull의 근거를 반박한 지점이 실제로 타당한지 판단한다. 타당한
  반박이면 그만큼 강세 논거의 신뢰도를 낮추고, Bear의 반박 자체가 억지스러우면 그 사실도 짚는다.
- **비대칭성 평가**: 강세 시나리오의 상방 여력과 약세 시나리오의 하방 리스크 중 어느 쪽이 더 크거나
  구체적인지 짚는다(둘 다 막연하면 "판단 근거 부족"으로 명시).
- **관찰 포인트**: 다음 판단이 바뀔 만한 조건 — 강세/약세 논거의 무효화 조건 중 특히 주목할 만한 것을
  추려 "지켜볼 지점"으로 남긴다.

강세/약세 중 하나가 명백히 근거가 부족하면 그 사실도 그대로 밝히고(예: "약세 근거는 뚜렷하지 않음"),
억지로 균형을 맞추지 마세요.

## 출력 형식
```
### 크립토 리서치 종합 (Node)
- **코인명**: 강세 논거 요약 / 약세 논거 요약(Bear 반박 반영) / 근거 품질 비교 → 비대칭성 판단 →
  균형 잡힌 시각 / 지켜볼 지점
...
```

## 주의사항
- 매수/매도 추천을 하지 않습니다. 최종 리포트 작성은 chief-strategist(The Boss)의 몫입니다.
- Bull/Bear가 제공하지 않은 사실을 지어내지 마세요.
- "반반이다"라는 식으로 얼버무리지 말고, 근거 품질 차이가 있다면 그 차이를 명시적으로 드러내세요.
- Bull과 Bear의 논거를 당신이 새로 쓰지 마세요 — 이미 나온 논거를 저울질하는 역할만 합니다.
```

- [ ] **Step 2: 옛 섹션이 사라졌는지 확인**

Run: `python -c "t=open('.claude/agents/node.md',encoding='utf-8').read(); assert '1. 강세 논거 세우기' not in t; assert '2. 약세 논거 세우기' not in t; assert '### 크립토 리서치 종합 (Node)' in t; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/node.md
git commit -m "refactor: Node를 Bull/Bear 토론 심판 역할로 축소"
```

---

### Task 4: 파이프라인 오케스트레이션 문서 갱신 (daily-report, scheduled-analysis)

**Files:**
- Modify: `.claude/commands/daily-report.md`
- Modify: `.claude/commands/scheduled-analysis.md`

**Interfaces:**
- Consumes: Task 1/2/3에서 정의한 `bull`/`bear`/`node` 서브에이전트 이름.

- [ ] **Step 1: `.claude/commands/daily-report.md`의 3번 단계 교체**

교체 전:
```markdown
3. **리서치팀 (데스크별 독립 진행)**: 아래 3개 데스크별 리서치 종합 담당에게 같은 데스크의 애널리스트 3명
   결과를 전달해 호출합니다. 세 데스크는 서로 완전히 독립적이므로 전체를 한꺼번에 병렬로 호출해도 됩니다.
   - 크립토 데스크: `candle`/`proto`/`vibes` 결과 → `node`에게 전달해 종합
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합
```

교체 후:
```markdown
3. **리서치팀 (데스크별 독립 진행)**: 데스크 간에는 서로 완전히 독립적이므로 병렬로 진행해도
   됩니다. 단 크립토 데스크는 내부적으로 순차 호출이 필요합니다(Bear가 Bull의 글을 읽고 반박해야
   하므로).
   - 크립토 데스크(순차): `candle`/`proto`/`vibes` 결과 → `bull`에게 전달해 강세 논거 작성 →
     `bull`의 결과를 `bear`에게 전달해 약세 논거+반박 작성 → `bull`/`bear` 결과를 모두 `node`에게
     전달해 저울질
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합
```

- [ ] **Step 2: `.claude/commands/scheduled-analysis.md`의 3번 단계 교체**

교체 전:
```markdown
3. **리서치팀 (데스크별 독립 진행)**: 세 데스크 모두 독립적이므로 한꺼번에 병렬로 호출해도 됩니다.
   - 크립토 데스크: `candle`/`proto`/`vibes` 결과 → `node`에게 전달해 종합
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합
```

교체 후:
```markdown
3. **리서치팀 (데스크별 독립 진행)**: 데스크 간에는 서로 완전히 독립적이므로 병렬로 진행해도
   됩니다. 단 크립토 데스크는 내부적으로 순차 호출이 필요합니다(Bear가 Bull의 글을 읽고 반박해야
   하므로).
   - 크립토 데스크(순차): `candle`/`proto`/`vibes` 결과 → `bull`에게 전달해 강세 논거 작성 →
     `bull`의 결과를 `bear`에게 전달해 약세 논거+반박 작성 → `bull`/`bear` 결과를 모두 `node`에게
     전달해 저울질
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합
```

- [ ] **Step 3: 두 파일 모두 `bull`/`bear` 언급이 들어갔는지 확인**

Run: `python -c "
for f in ['.claude/commands/daily-report.md', '.claude/commands/scheduled-analysis.md']:
    t = open(f, encoding='utf-8').read()
    assert '\`bull\`' in t and '\`bear\`' in t, f
print('OK')
"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/daily-report.md .claude/commands/scheduled-analysis.md
git commit -m "docs: daily-report/scheduled-analysis 파이프라인에 Bull/Bear 순차 호출 반영"
```

---

### Task 5: chief-strategist 파이프라인 설명 + 리포트 템플릿에 Bull/Bear 반영

**Files:**
- Modify: `.claude/agents/chief-strategist.md`

**Interfaces:**
- Consumes: Task 1/2에서 정의한 `### 크립토 강세 논거 (Bull)` / `### 크립토 약세 논거 (Bear)` 헤더.

- [ ] **Step 1: 역할 설명의 크립토 데스크 파이프라인 줄 교체**

교체 전 (파일 14-15번째 줄 부근):
```markdown
- **크립토 데스크**: Candle(기술적분석), Proto(펀더멘털), Vibes(뉴스·심리) → Node(리서치 종합)
  → Trigger(매매 시그널 생성) → Maverick/Guardian(리스크 검토) → Balance(최종 권고) *(2단계, 크립토 파일럿)*
```

교체 후:
```markdown
- **크립토 데스크**: Candle(기술적분석), Proto(펀더멘털), Vibes(뉴스·심리) → Bull(강세 논거)
  → Bear(약세 논거·반박) → Node(저울질) → Trigger(매매 시그널 생성) → Maverick/Guardian(리스크 검토)
  → Balance(최종 권고) *(2단계, 크립토 파일럿)*
```

- [ ] **Step 2: 리포트 템플릿에 Bull/Bear 섹션 헤더 추가**

교체 전:
```markdown
## Vibes - 암호화폐 뉴스·심리
(vibes 결과 원문)

## Node - 크립토 리서치 종합
(node 결과 원문)
```

교체 후:
```markdown
## Vibes - 암호화폐 뉴스·심리
(vibes 결과 원문)

## Bull - 크립토 강세 논거
(bull 결과 원문)

## Bear - 크립토 약세 논거
(bear 결과 원문)

## Node - 크립토 리서치 종합
(node 결과 원문)
```

- [ ] **Step 3: 헤더가 정확히 들어갔는지 확인**

Run: `python -c "t=open('.claude/agents/chief-strategist.md',encoding='utf-8').read(); assert '## Bull - 크립토 강세 논거' in t; assert '## Bear - 크립토 약세 논거' in t; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/chief-strategist.md
git commit -m "docs: chief-strategist 파이프라인 설명·리포트 템플릿에 Bull/Bear 반영"
```

---

### Task 6: `office_data.py`에 Bull/Bear 오피스 카드 추가 + watchlist 필터 보정

**Files:**
- Modify: `scripts/office_data.py:15-198` (EMPLOYEES 리스트), `scripts/office_data.py:277-292` (상수),
  `scripts/office_data.py:359-367` (watchlist team_employees 필터)

**Interfaces:**
- Consumes: Task 1/2에서 정의한 report section 헤더 `"Bull - 크립토 강세 논거"`,
  `"Bear - 크립토 약세 논거"`.
- Produces: `EMPLOYEES`에 id `"bull"`/`"bear"` 항목 추가(오피스 UI에 카드로 표시됨). 이 두 id는
  `WATCHLIST_EXCLUDE_IDS`에도 등록되어, 이후 Task 8이 참조하는 watchlist 카드 조립 로직에서
  제외된다.

**배경(중요):** `EMPLOYEES`에서 `subteam == "RESEARCH"`인 항목은 두 가지 용도로 동시에 쓰인다 —
(1) 오피스 UI에서 "리서치" 층에 카드로 표시, (2) `build_office_data`의 watchlist 카드 조립
로직(줄 363)이 "종목카드에는 데스크 리서치 종합만 보여준다"는 기존 설계 의도로 `subteam ==
"RESEARCH"`인 에이전트의 텍스트만 종목별로 재매칭한다. Bull/Bear를 그냥 `subteam: "RESEARCH"`로만
추가하면 (1)은 원하는 대로 되지만 (2)도 함께 적용돼 Bull/Bear의 중간 토론 문장까지 watchlist
카드에 섞여 들어간다 — 기존 주석("종목카드에는 애널리스트 개별 원문이 아니라 데스크 리서치 종합만
보여준다")과 어긋난다. 그래서 watchlist 카드 조립에서만 Bull/Bear를 명시적으로 제외한다.

- [ ] **Step 1: EMPLOYEES에 bull/bear 항목 추가**

`scripts/office_data.py`에서 `vibes` 항목(48번째 줄, `},`로 끝남)과 `node` 항목(49번째 줄
`{`로 시작) 사이에 아래 두 항목을 삽입한다.

```python
    {
        "id": "bull",
        "name": "Bull",
        "role": "크립토 강세 논거",
        "emoji": "🐂",
        "color": "#e0ffe6",
        "team": "크립토",
        "subteam": "RESEARCH",
        "report_sections": ["Bull - 크립토 강세 논거"],
        "raw_data_glob": None,
    },
    {
        "id": "bear",
        "name": "Bear",
        "role": "크립토 약세 논거",
        "emoji": "🐻",
        "color": "#ffe0e0",
        "team": "크립토",
        "subteam": "RESEARCH",
        "report_sections": ["Bear - 크립토 약세 논거"],
        "raw_data_glob": None,
    },
```

- [ ] **Step 2: watchlist 제외 목록 상수 추가**

`WATCHLIST_KEY`/`WATCHLIST_MATCH_FIELD` 정의부(277-281번째 줄) 바로 아래에 추가:

```python
# Bull/Bear는 Node가 저울질하기 전 중간 토론 산출물이라, watchlist 카드에는 최종 종합(Node/
# Anchor/Compass)만 남기고 제외한다.
WATCHLIST_EXCLUDE_IDS = {"bull", "bear"}
```

- [ ] **Step 3: watchlist team_employees 필터에 제외 조건 적용**

`build_office_data` 안의 아래 줄(교체 전, 약 363번째 줄):
```python
        team_employees = [e for e in EMPLOYEES if e["team"] == team and e.get("subteam") == "RESEARCH"]
```
교체 후:
```python
        team_employees = [
            e
            for e in EMPLOYEES
            if e["team"] == team
            and e.get("subteam") == "RESEARCH"
            and e["id"] not in WATCHLIST_EXCLUDE_IDS
        ]
```

- [ ] **Step 4: 동작 확인**

Run:
```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from office_data import EMPLOYEES, WATCHLIST_EXCLUDE_IDS
ids = [e['id'] for e in EMPLOYEES]
assert 'bull' in ids and 'bear' in ids
assert WATCHLIST_EXCLUDE_IDS == {'bull', 'bear'}
print('OK')
"
```
Expected: `OK`

- [ ] **Step 5: `python scripts\generate_office.py` 실행해 에러 없이 끝나는지 확인**

Run: `python scripts\generate_office.py`
Expected: 에러 없이 종료, `office/index.html`이 갱신됨(이 시점엔 아직 리포트에 Bull/Bear 섹션이
없을 수 있으므로 해당 카드는 "대기 중" 상태로 보이는 게 정상).

- [ ] **Step 6: Commit**

```bash
git add scripts/office_data.py
git commit -m "feat: 오피스 EMPLOYEES에 Bull/Bear 카드 추가, watchlist 카드는 Node 종합만 유지"
```

---

### Task 7: Trigger 출력에 구조화 JSON 블록 추가

**Files:**
- Modify: `.claude/agents/trigger.md`

**Interfaces:**
- Produces: Trigger 마크다운 출력 뒤에 오는 fenced JSON 블록. 스키마:
  `{"signals": [{"symbol": str, "direction": "buy"|"sell"|"hold", "entry": number|null, "target": number|null, "stop": number|null, "position_pct": number, "rr": number|null}]}`.
  Task 8의 `parse_json_block`이 이 스키마를 그대로 파싱한다.

- [ ] **Step 1: `.claude/agents/trigger.md`의 "## 출력 형식" 섹션 뒤에 JSON 지시 추가**

교체 전 (파일 48-54번째 줄):
```markdown
## 출력 형식
```
### 크립토 매매 시그널 (Trigger)
- **코인명**: 방향(매수/매도/관망) · 진입가 · 목표가 · 손절가 · 포지션 크기(총자본 대비 %) · 근거(Node 인용)
  (관망인 코인은 "진입가/목표가/손절가: 해당 없음"으로 표기하고 관망 이유만 남깁니다)
...
```
```

교체 후:
```markdown
## 출력 형식
```
### 크립토 매매 시그널 (Trigger)
- **코인명**: 방향(매수/매도/관망) · 진입가 · 목표가 · 손절가 · 포지션 크기(총자본 대비 %) · 근거(Node 인용)
  (관망인 코인은 "진입가/목표가/손절가: 해당 없음"으로 표기하고 관망 이유만 남깁니다)
...
```

위 마크다운 뒤에 이어서, 같은 내용을 아래 스키마의 fenced JSON 블록으로도 출력합니다(마크다운을
대체하는 게 아니라 병행 출력입니다 — 오피스 화면이 기계적으로 파싱할 수 있게 하기 위함).

```
```json
{"signals":[{"symbol":"ETH","direction":"buy","entry":2702000,"target":2727000,"stop":2699200,"position_pct":3,"rr":8.9}]}
```
```

- `direction`은 `"buy"`/`"sell"`/`"hold"` 중 하나만 씁니다.
- `hold`인 코인은 `entry`/`target`/`stop`/`rr`을 `null`로, `position_pct`는 `0`으로 씁니다.
- `symbol`은 위 마크다운에서 쓴 것과 동일한 심볼(예: BTC, ETH)을 대문자로 씁니다.
- watchlist에 있는 코인은 관망이라도 반드시 `signals` 배열에 포함시킵니다(빠뜨리지 않습니다).
```

- [ ] **Step 2: JSON 스키마 문구가 들어갔는지 확인**

Run: `python -c "t=open('.claude/agents/trigger.md',encoding='utf-8').read(); assert '\`\`\`json' in t; assert '\"signals\"' in t; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/trigger.md
git commit -m "feat: Trigger 출력에 구조화 JSON 시그널 블록 병행 출력 지시 추가"
```

---

### Task 8: `office_data.py`에 JSON 시그널 파서 추가 + watchlist 카드에 병합 + self-check

**Files:**
- Modify: `scripts/office_data.py`
- Create: `scripts/test_office_data.py`

**Interfaces:**
- Consumes: Task 7이 정의한 Trigger의 fenced JSON 스키마.
- Produces: `parse_json_block(text: str) -> dict | None` — 함수명·시그니처 확정. 성공 시
  `{"ETH": {"symbol": "ETH", "direction": "buy", ...}, ...}` 형태(심볼 대문자 키)의 dict를
  반환하고, JSON 블록이 없거나 파싱 실패하면 `None`을 반환한다(예외를 던지지 않는다).
  크립토 watchlist 카드(`build_office_data`가 만드는 `watchlistGroups`의 `items`)에 이 함수의
  결과가 있으면 `signal` 필드로 병합된다.

- [ ] **Step 1: `scripts/test_office_data.py` 작성 (아직 없는 함수를 테스트 — 실패해야 정상)**

```python
"""office_data.py의 parse_json_block()과 EMPLOYEES 구성을 점검하는 최소 self-check.
이 저장소엔 pytest 등 테스트 프레임워크가 없어 `python scripts/test_office_data.py`로 직접
실행한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from office_data import EMPLOYEES, WATCHLIST_EXCLUDE_IDS, parse_json_block


def test_parse_json_block_valid():
    text = (
        "### 크립토 매매 시그널 (Trigger)\n"
        "- ETH: 매수...\n\n"
        "```json\n"
        '{"signals":[{"symbol":"ETH","direction":"buy","entry":2702000,'
        '"target":2727000,"stop":2699200,"position_pct":3,"rr":8.9}]}\n'
        "```\n"
    )
    result = parse_json_block(text)
    assert result is not None, "JSON 블록을 찾지 못함"
    assert result["ETH"]["direction"] == "buy"
    assert result["ETH"]["entry"] == 2702000


def test_parse_json_block_missing():
    assert parse_json_block("그냥 텍스트, JSON 블록 없음") is None


def test_parse_json_block_malformed():
    text = "```json\n{이건 JSON이 아님}\n```"
    assert parse_json_block(text) is None


def test_parse_json_block_no_signals_key():
    text = '```json\n{"foo": "bar"}\n```'
    assert parse_json_block(text) is None


def test_employees_have_bull_bear_excluded_from_watchlist():
    ids = [e["id"] for e in EMPLOYEES]
    assert "bull" in ids and "bear" in ids
    assert WATCHLIST_EXCLUDE_IDS == {"bull", "bear"}


if __name__ == "__main__":
    test_parse_json_block_valid()
    test_parse_json_block_missing()
    test_parse_json_block_malformed()
    test_parse_json_block_no_signals_key()
    test_employees_have_bull_bear_excluded_from_watchlist()
    print("OK - all office_data self-checks passed")
```

- [ ] **Step 2: self-check 실행 → import 에러로 실패하는지 확인 (parse_json_block 아직 없음)**

Run: `python scripts\test_office_data.py`
Expected: `ImportError: cannot import name 'parse_json_block' from 'office_data'` (또는 동일한
취지의 ImportError)로 실패.

- [ ] **Step 3: `scripts/office_data.py`에 `parse_json_block` 구현**

`match_symbol_lines` 함수(292번째 줄) 바로 아래에 추가:

```python
JSON_SIGNAL_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def parse_json_block(text: str) -> dict | None:
    match = JSON_SIGNAL_BLOCK_RE.search(text)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    signals = data.get("signals")
    if not isinstance(signals, list):
        return None
    result = {}
    for entry in signals:
        if not isinstance(entry, dict):
            continue
        symbol = entry.get("symbol")
        if symbol:
            result[str(symbol).upper()] = entry
    return result
```

- [ ] **Step 4: self-check 재실행 → 통과 확인**

Run: `python scripts\test_office_data.py`
Expected: `OK - all office_data self-checks passed`

- [ ] **Step 5: `build_office_data`에서 Trigger 시그널을 크립토 watchlist 카드에 병합**

`build_office_data` 함수 안, `watchlist = watchlist_store.load()` 줄(357번째 줄) 바로 앞에 추가:

```python
    trigger_signals = parse_json_block(emp_full_text.get("trigger", "")) or {}
```

이어서 카드 조립 루프의 아래 부분(교체 전, 약 372-377번째 줄):
```python
            notes = []
            for emp in team_employees:
                for line in match_symbol_lines(emp_full_text.get(emp["id"], ""), match_key):
                    notes.append({"name": emp["name"], "emoji": emp["emoji"], "text": line})

            cards.append({"key": match_key, "label": label, "notes": notes})
```
교체 후:
```python
            notes = []
            for emp in team_employees:
                for line in match_symbol_lines(emp_full_text.get(emp["id"], ""), match_key):
                    notes.append({"name": emp["name"], "emoji": emp["emoji"], "text": line})

            card = {"key": match_key, "label": label, "notes": notes}
            if wl_key == "crypto":
                signal = trigger_signals.get(match_key.upper())
                if signal:
                    card["signal"] = signal
            cards.append(card)
```

- [ ] **Step 6: 통합 동작 확인 (실제 리포트 파일로)**

Run:
```bash
python -c "
import sys; sys.path.insert(0, 'scripts')
from office_data import build_office_data
data = build_office_data()
crypto = next((g for g in data['watchlistGroups'] if g['category'] == '크립토'), None)
print('crypto group found:', crypto is not None)
if crypto:
    for item in crypto['items']:
        print(item['key'], '-> signal:', item.get('signal'))
"
```
Expected: 에러 없이 실행됨. `reports/`에 아직 Trigger의 JSON 블록이 없는 과거 리포트만 있다면
`signal`은 모두 `None`으로 나오는 게 정상 — 이 스텝은 "에러 없이 끝나는지"만 확인한다.

- [ ] **Step 7: `python scripts\generate_office.py` 최종 확인**

Run: `python scripts\generate_office.py`
Expected: 에러 없이 종료.

- [ ] **Step 8: Commit**

```bash
git add scripts/office_data.py scripts/test_office_data.py
git commit -m "feat: Trigger JSON 시그널 파서 추가, 크립토 watchlist 카드에 signal 필드 병합"
```

---

## 최종 통합 검증 (모든 태스크 완료 후)

- [ ] `/daily-report` 1회 실행
- [ ] `reports/YYYY-MM-DD.md`에 "Bull - 크립토 강세 논거", "Bear - 크립토 약세 논거" 섹션이 있고,
      Bear 섹션이 Bull의 실제 문장을 인용해 반박하는지 육안 확인
- [ ] Node 섹션이 스스로 강세/약세를 새로 쓰지 않고 Bull/Bear 인용 기반 저울질만 하는지 확인
- [ ] 오피스 UI(`office/index.html`)에서 크립토 RESEARCH 존에 Bull/Bear 카드가 Node 앞 순서로
      보이는지 확인
- [ ] 크립토 watchlist 카드의 notes에 Bull/Bear 문장이 섞이지 않고 Node 문장만 보이는지 확인
- [ ] Trigger 섹션 원문에 fenced JSON 블록이 포함돼 있는지, `python scripts\test_office_data.py`가
      `OK`를 출력하는지 확인
