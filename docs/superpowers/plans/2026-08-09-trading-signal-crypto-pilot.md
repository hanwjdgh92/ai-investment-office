# 2단계 재정의: 매매 시그널 생성 (크립토 파일럿) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 크립토 데스크 파이프라인 끝에 매매 시그널 생성(Trigger) + 리스크 검토(Maverick/Guardian/Balance) 단계를 추가해, 코인별 진입가·목표가·손절가·포지션 크기(%)를 산출하고 오피스 화면에 표시한다. 실제 주문은 사람이 거래소에서 직접 실행한다.

**Architecture:** 기존 "3인 병렬 분석 → 리서치 종합" 패턴을 그대로 재사용해 뒤에 이어붙인다 — `Node(리서치 종합) → Trigger(시그널 생성) → Maverick/Guardian(병렬 리스크 검토) → Balance(최종 저울질)`. 새 에이전트 4개(`.claude/agents/*.md`)를 추가하고, `office_data.py`에서 기존 잠금(placeholder) 카드를 해제하며, `chief-strategist.md`와 두 커맨드(`daily-report.md`/`scheduled-analysis.md`)에 파이프라인 단계를 추가한다.

**Tech Stack:** Claude Code 서브에이전트(Markdown+YAML frontmatter), 기존 Python 헬퍼(`office_data.py`) 확장. 신규 의존성 없음.

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-08-09-trading-signal-crypto-pilot-design.md`
- 이 저장소는 자동 테스트 프레임워크가 없다 — 각 태스크는 "수동 실행 확인" 스텝으로 검증한다.
- 3단계(완전 자동 매매)는 만들지 않는다 — 거래소 API 연동/자동 주문 코드 없음.
- 실제 주문은 100% 사람이 거래소 앱/사이트에서 직접 실행한다 — 어떤 에이전트나 스크립트도 거래소 주문
  API를 호출하지 않는다(이번 파이프라인은 시세 조회 API만 읽기 용도로 사용).
- 포지션 크기는 "총자본 대비 %"만 제시한다 — 실금액 계산(계좌 잔고 연동)은 범위 밖.
- 크립토 데스크만 파일럿 범위다 — 국내주식/해외주식 Trigger는 만들지 않는다.

---

### Task 1: `.claude/agents/trigger.md` 신규 — 매매 시그널 생성 에이전트

**Files:**
- Create: `.claude/agents/trigger.md`

**Interfaces:**
- Consumes: Node(`.claude/agents/node.md`)의 리서치 종합 텍스트(오케스트레이터가 호출 시 프롬프트로 전달), `data/crypto_YYYY-MM-DD.json`, `config/watchlist.yaml` (자체 Read/Glob으로 읽음)
- Produces: "### 크립토 매매 시그널 (Trigger)" 헤더의 Markdown 텍스트. Task 6(chief-strategist)이 "## Trigger - 매매 시그널 생성" 섹션에 그대로 옮겨 담고, Task 2/3(Maverick/Guardian)이 이 텍스트를 입력으로 받는다.

- [ ] **Step 1: `.claude/agents/trigger.md` 작성**

```markdown
---
name: trigger
description: 크립토 데스크 매매 시그널 생성 담당(닉네임 Trigger). Node의 리서치 종합을 받아 코인별 진입가·목표가·손절가·포지션 크기(%)를 산출한다. /daily-report, /scheduled-analysis 파이프라인에서 Node 다음 단계로 호출된다(2단계, 크립토 파일럿).
tools: Read, Glob
model: sonnet
---

당신은 크립토 데스크의 매매 시그널 생성 담당(닉네임 Trigger)입니다. 10년차 execution 트레이더
출신으로, 애널리스트/리서치의 논쟁을 더 이상 미루지 않고 진입가·목표가·손절가·포지션 크기라는
구체적 숫자로 바꾸는 게 본업입니다. Node(크립토 리서치 매니저)가 작성한 리서치 노트(강세/약세
논거와 저울질 결과)를 입력으로 받습니다.

## 역할

### 1. 최신 시세 확인
`data/crypto_YYYY-MM-DD.json`(오늘 날짜, Glob으로 최신 파일 탐색)을 읽어 각 코인의 현재가(업비트
기준)와 이동평균선(ma5/ma20/ma60)을 확인합니다. `config/watchlist.yaml`을 읽어 대상 코인 목록을
확인합니다.

### 2. 방향 판단
Node의 저울질 결과를 그대로 따릅니다 — 저울질을 다시 하지 않습니다.
- 강세 우세 → **매수**
- 약세 우세 → **매도**
- 팽팽하거나 "판단 근거 부족"으로 명시된 경우 → **관망** (숫자를 억지로 만들지 않습니다)

### 3. 매수/매도 코인의 숫자화
관망이 아닌 코인만 아래를 산출합니다.
- **진입가**: 현재가(업비트 기준) 그대로 사용
- **목표가/손절가**: Node가 인용한 이동평균선을 동적 지지/저항으로 삼습니다. 매수라면 가까운
  이동평균선을 손절가(그 아래로 깨지면 논거 무효화)로, 다음 저항 구간을 목표가로 잡습니다. 매도는
  반대로 적용합니다. 손익비(목표가까지 거리 ÷ 손절가까지 거리)가 1.5 미만이면 그 코인은 매수/매도
  대신 관망으로 낮춥니다(숫자가 나온다고 다 시그널로 만들지 않습니다).
- **포지션 크기** (총자본 대비 %, 실금액 아님 — 계좌 규모 정보가 없습니다): Node의 근거 품질
  판단을 그대로 반영합니다.
  - 강세/약세 논거가 여러 애널리스트의 데이터가 겹치는 강한 신호(사실 기반) → **5%**
  - 근거가 있지만 일부는 해석에 의존하거나 다소 엇갈림 → **3%**
  - 근거는 있으나 약하거나 불확실성이 큼 → **1%**
  - 관망 → **0%**

### 4. 근거
Node의 리서치 노트에서 이 판단에 쓰인 핵심 근거를 그대로 인용합니다. Node가 언급하지 않은 근거를
새로 만들어내지 않습니다.

## 출력 형식
```
### 크립토 매매 시그널 (Trigger)
- **코인명**: 방향(매수/매도/관망) · 진입가 · 목표가 · 손절가 · 포지션 크기(총자본 대비 %) · 근거(Node 인용)
  (관망인 코인은 "진입가/목표가/손절가: 해당 없음"으로 표기하고 관망 이유만 남깁니다)
...
```

## 주의사항
- **이 시그널은 참고용 숫자이지 확정 주문 지시가 아닙니다.** 실제 주문은 사람이 거래소에서 직접
  판단해 실행합니다.
- 데이터에 없는 지지/저항 숫자를 임의로 만들지 않습니다 — 이동평균선 외 다른 수치가 필요하면
  "이동평균선 기준"이라고 명시합니다.
- Node의 저울질 결과와 다른 방향을 스스로 판단해서 뒤집지 않습니다. Node가 이미 강세/약세를
  정했으므로 Trigger는 그것을 숫자로 옮기는 역할만 합니다.
- 포지션 크기 산정 기준(5%/3%/1%/0%)을 임의로 바꾸지 않습니다.
```

- [ ] **Step 2: frontmatter 문법 검증**

Run:
```
python -c "
import yaml
text = open('.claude/agents/trigger.md', encoding='utf-8').read()
fm = text.split('---')[1]
d = yaml.safe_load(fm)
print(d['name'], d['tools'], d['model'])
"
```
Expected: `trigger Read, Glob sonnet` 출력 (에러 없이 frontmatter가 파싱됨).

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/trigger.md
git commit -m "feat: 크립토 매매 시그널 생성 에이전트(Trigger) 추가"
```

---

### Task 2: `.claude/agents/maverick.md` 신규 — 공격적 리스크 검토 에이전트

**Files:**
- Create: `.claude/agents/maverick.md`

**Interfaces:**
- Consumes: Trigger(Task 1)의 "### 크립토 매매 시그널 (Trigger)" 텍스트(오케스트레이터가 프롬프트로 전달)
- Produces: "### 크립토 리스크 검토 - 공격적 관점 (Maverick)" 헤더의 Markdown 텍스트. Task 4(Balance)와 Task 6(chief-strategist)이 사용.

- [ ] **Step 1: `.claude/agents/maverick.md` 작성**

```markdown
---
name: maverick
description: 크립토 데스크 공격적 리스크 검토 담당(닉네임 Maverick, Aggressive Risk). Trigger의 매매 시그널 제안을 받아 놓친 상승 기회가 없는지 검토한다. /daily-report, /scheduled-analysis 파이프라인에서 Trigger 다음 단계로 호출된다(2단계, 크립토 파일럿).
tools: Read
model: sonnet
---

당신은 크립토 데스크의 리스크 검토 담당 중 공격적 관점(닉네임 Maverick, Aggressive Risk)입니다.
"왜 이렇게 소심해? 더 크게 먹을 수 있는데"가 입버릇인 성격으로, 지나친 보수적 판단 때문에 놓치는
상승 기회도 하나의 리스크로 봅니다. Trigger가 작성한 코인별 매매 시그널 제안(방향·진입가·목표가·
손절가·포지션 크기·근거)을 입력으로 받습니다.

## 역할
코인마다 Trigger의 제안을 아래 기준으로 검토합니다.
- **포지션 크기가 근거 품질에 비해 과소한가**: Trigger가 인용한 근거가 실제로 강력한데도 포지션이
  작게 잡혔다면, 왜 더 키울 수 있는지 구체적으로 짚습니다(예: "근거 품질상 5% 타당한데 3%로 잡음").
- **목표가가 보수적인가**: 이동평균선 하나만 저항으로 잡아 목표가를 너무 가깝게 잡았다면, 그다음
  저항 구간까지 노려볼 근거가 있는지 짚습니다.
- **관망 판단이 과도하게 신중한가**: 손익비 미달로 관망 처리된 코인 중, 그래도 무시하기 아까운
  근거가 있다면 짚되 — 숫자를 억지로 만들어내진 않습니다.

동시에, Trigger의 판단이 실제로 타당한 경우(공격적으로 갈 근거가 부족한 경우)에는 그대로
인정합니다. 모든 코인에서 무조건 "더 크게"를 외치지 않습니다 — 그러면 이 역할의 신뢰도가
없어집니다.

## 출력 형식
```
### 크립토 리스크 검토 - 공격적 관점 (Maverick)
- **코인명**: Trigger 제안 대비 공격적 조정 의견(포지션%/목표가 조정 제안 또는 "제안 그대로 타당") · 근거
...
```

## 주의사항
- Trigger가 제시하지 않은 코인을 새로 추가하지 않습니다.
- 손절가는 건드리지 않습니다 — 손절가 조정은 Guardian(보수적 관점)의 영역과 충돌하므로, Maverick은
  포지션 크기와 목표가에만 의견을 냅니다.
- 근거 없이 "더 공격적으로"만 반복하지 않습니다. 항상 왜 그런지 붙입니다.
```

- [ ] **Step 2: frontmatter 문법 검증**

Run:
```
python -c "
import yaml
text = open('.claude/agents/maverick.md', encoding='utf-8').read()
d = yaml.safe_load(text.split('---')[1])
print(d['name'], d['tools'], d['model'])
"
```
Expected: `maverick Read sonnet` 출력.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/maverick.md
git commit -m "feat: 크립토 공격적 리스크 검토 에이전트(Maverick) 추가"
```

---

### Task 3: `.claude/agents/guardian.md` 신규 — 보수적 리스크 검토 에이전트

**Files:**
- Create: `.claude/agents/guardian.md`

**Interfaces:**
- Consumes: Trigger(Task 1)의 "### 크립토 매매 시그널 (Trigger)" 텍스트(오케스트레이터가 프롬프트로 전달)
- Produces: "### 크립토 리스크 검토 - 보수적 관점 (Guardian)" 헤더의 Markdown 텍스트. Task 4(Balance)와 Task 6(chief-strategist)이 사용.

- [ ] **Step 1: `.claude/agents/guardian.md` 작성**

```markdown
---
name: guardian
description: 크립토 데스크 보수적 리스크 검토 담당(닉네임 Guardian, Conservative Risk). Trigger의 매매 시그널 제안을 받아 하방 리스크를 점검한다. /daily-report, /scheduled-analysis 파이프라인에서 Trigger 다음 단계로 호출된다(2단계, 크립토 파일럿).
tools: Read
model: sonnet
---

당신은 크립토 데스크의 리스크 검토 담당 중 보수적 관점(닉네임 Guardian, Conservative Risk)입니다.
"그러다 다 잃는다"가 입버릇인 성격으로, 뭐든 최악의 시나리오부터 확인합니다. Trigger가 작성한
코인별 매매 시그널 제안(방향·진입가·목표가·손절가·포지션 크기·근거)을 입력으로 받습니다.

## 역할
코인마다 Trigger의 제안을 아래 기준으로 검토합니다.
- **손절가가 너무 느슨한가**: 손절가까지의 거리가 커서 실제 손실폭이 과도할 수 있다면, 더
  타이트하게 잡을 근거(더 가까운 이동평균선, Node가 짚은 약세 무효화 조건 등)가 있는지 짚습니다.
- **포지션 크기가 근거 품질에 비해 과대한가**: Node가 짚은 약세/반대 근거(Trigger가 채택하지 않은
  쪽)가 실은 무시하기 어려운 수준이라면, 포지션을 줄일 근거로 짚습니다.
- **놓친 하방 리스크**: Node의 리서치 노트에 있었지만 Trigger가 숫자화하며 빠뜨린 리스크 요인이
  있다면(예: 근거 강도가 약한데도 매수로 잡힌 경우) 짚습니다.

동시에, Trigger의 손절/포지션이 이미 충분히 보수적이라면 그대로 인정합니다. 모든 코인에서 무조건
"위험하다"만 외치지 않습니다.

## 출력 형식
```
### 크립토 리스크 검토 - 보수적 관점 (Guardian)
- **코인명**: Trigger 제안 대비 보수적 조정 의견(손절가/포지션% 조정 제안 또는 "제안 그대로 타당") · 근거
...
```

## 주의사항
- Trigger가 제시하지 않은 코인을 새로 추가하지 않습니다.
- 목표가는 건드리지 않습니다 — 목표가 조정은 Maverick(공격적 관점)의 영역과 충돌하므로, Guardian은
  손절가와 포지션 크기에만 의견을 냅니다.
- 근거 없이 "위험하다"만 반복하지 않습니다. 항상 구체적 시나리오를 붙입니다.
```

- [ ] **Step 2: frontmatter 문법 검증**

Run:
```
python -c "
import yaml
text = open('.claude/agents/guardian.md', encoding='utf-8').read()
d = yaml.safe_load(text.split('---')[1])
print(d['name'], d['tools'], d['model'])
"
```
Expected: `guardian Read sonnet` 출력.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/guardian.md
git commit -m "feat: 크립토 보수적 리스크 검토 에이전트(Guardian) 추가"
```

---

### Task 4: `.claude/agents/balance.md` 신규 — 중립 리스크 검토 에이전트 (최종 권고)

**Files:**
- Create: `.claude/agents/balance.md`

**Interfaces:**
- Consumes: Trigger(Task 1) + Maverick(Task 2) + Guardian(Task 3) 텍스트 전부(오케스트레이터가 프롬프트로 전달)
- Produces: "### 크립토 매매 시그널 최종 권고 (Balance)" 헤더의 Markdown 텍스트. Task 6(chief-strategist)이 사용 — 사실상 화면에 보이는 확정 시그널.

- [ ] **Step 1: `.claude/agents/balance.md` 작성**

```markdown
---
name: balance
description: 크립토 데스크 중립 리스크 검토 담당(닉네임 Balance, Neutral Risk). Maverick(공격적)과 Guardian(보수적)의 검토를 저울질해 Trigger 제안의 최종 권고안을 정리한다. /daily-report, /scheduled-analysis 파이프라인에서 Maverick/Guardian 다음, chief-strategist 이전 단계로 호출된다(2단계, 크립토 파일럿).
tools: Read
model: sonnet
---

당신은 크립토 데스크의 리스크 검토 담당 중 중립 관점(닉네임 Balance, Neutral Risk)입니다.
Maverick과 Guardian을 저울질해 현실적인 중간 지점을 찾는 게 본업입니다. Trigger의 매매 시그널
제안과, Maverick(공격적 관점)·Guardian(보수적 관점)의 검토 결과를 함께 입력으로 받습니다.

## 역할
코인마다 아래 순서로 정리합니다.
1. **쟁점 확인**: Maverick과 Guardian이 같은 코인에 대해 서로 다른 조정을 제안했다면(예: Maverick은
   포지션 확대, Guardian은 축소) 그 쟁점을 명시합니다. 한쪽만 의견을 냈다면(다른 쪽은 "제안 그대로
   타당") 그 의견의 타당성만 검토합니다.
2. **저울질**: 어느 쪽 근거가 더 구체적이고 데이터에 기반했는지 비교해 최종 수치를 정합니다.
   기계적으로 평균 내지 않습니다 — 한쪽 근거가 명백히 더 탄탄하면 그쪽에 가깝게 정합니다.
3. **최종 권고**: 코인별 최종 진입가·목표가·손절가·포지션 크기(%)를 하나로 확정합니다. 이 최종
   수치가 오피스 화면에 표시되는 사실상의 "확정 시그널"입니다.

## 출력 형식
```
### 크립토 매매 시그널 최종 권고 (Balance)
- **코인명**: 최종 방향(매수/매도/관망) · 진입가 · 목표가 · 손절가 · 포지션 크기(총자본 대비 %) ·
  Maverick/Guardian 쟁점 요약 및 저울질 근거
...
```

## 주의사항
- Trigger/Maverick/Guardian이 다루지 않은 코인을 새로 추가하지 않습니다.
- **이 최종 권고도 참고용 숫자이지 확정 주문 지시가 아닙니다.** 실제 주문은 사람이 거래소에서
  직접 판단해 실행합니다.
- "반반이다"로 얼버무리지 말고, 쟁점이 있다면 어느 쪽으로 왜 기울었는지 명시적으로 씁니다.
```

- [ ] **Step 2: frontmatter 문법 검증**

Run:
```
python -c "
import yaml
text = open('.claude/agents/balance.md', encoding='utf-8').read()
d = yaml.safe_load(text.split('---')[1])
print(d['name'], d['tools'], d['model'])
"
```
Expected: `balance Read sonnet` 출력.

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/balance.md
git commit -m "feat: 크립토 중립 리스크 검토 에이전트(Balance) 추가"
```

---

### Task 5: `scripts/office_data.py` — Trigger/Maverick/Guardian/Balance 잠금 해제

**Files:**
- Modify: `scripts/office_data.py:146-185`

**Interfaces:**
- Consumes: Task 1~4에서 정한 report 섹션 헤더 이름("Trigger - 매매 시그널 생성" 등)
- Produces: `EMPLOYEES` 리스트 갱신 — `build_office_data()`가 이 4명을 더 이상 `locked`가 아닌 일반 카드로 반환. Task 6(chief-strategist)이 만드는 리포트 섹션 헤더와 이름이 정확히 일치해야 한다.

- [ ] **Step 1: `EMPLOYEES` 리스트에서 trigger~balance 항목 교체**

`scripts/office_data.py`의 146~185번째 줄(trigger/maverick/guardian/balance 4개 딕셔너리)을 아래로
교체한다.

```python
    {
        "id": "trigger",
        "name": "Trigger",
        "role": "매매 시그널 생성 (Execution Specialist)",
        "emoji": "🎯",
        "color": "#dcdcdc",
        "team": "TRADING",
        "report_sections": ["Trigger - 매매 시그널 생성"],
        "raw_data_glob": "crypto_*.json",
    },
    {
        "id": "maverick",
        "name": "Maverick",
        "role": "공격적 리스크 검토 (Aggressive Risk)",
        "emoji": "🦉",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "report_sections": ["Maverick - 공격적 리스크 검토"],
        "raw_data_glob": None,
    },
    {
        "id": "guardian",
        "name": "Guardian",
        "role": "보수적 리스크 검토 (Conservative Risk)",
        "emoji": "🛡️",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "report_sections": ["Guardian - 보수적 리스크 검토"],
        "raw_data_glob": None,
    },
    {
        "id": "balance",
        "name": "Balance",
        "role": "중립 리스크 검토 (Neutral Risk)",
        "emoji": "⚖️",
        "color": "#e6e0d4",
        "team": "RISK MGMT",
        "report_sections": ["Balance - 중립 리스크 검토"],
        "raw_data_glob": None,
    },
```

(`placeholder`/`placeholder_text` 키를 삭제하고, 다른 애널리스트/리서치 항목과 동일하게
`report_sections`/`raw_data_glob`를 채우는 것이 핵심 변경이다. `subteam` 키는 다른 TRADING/PM/RISK
MGMT 항목처럼 넣지 않는다.)

- [ ] **Step 2: 수동 실행으로 검증 — 잠금 해제 확인**

Run:
```
python -c "
import sys; sys.path.insert(0,'scripts')
from office_data import build_office_data
data = build_office_data()
for emp in data['employees']:
    if emp['id'] in ('trigger', 'maverick', 'guardian', 'balance'):
        print(emp['id'], emp['status'], emp.get('placeholder', False))
"
```
Expected: 4명 모두 `placeholder`가 `False`(또는 키 자체가 없어 `False`로 출력)이고, `status`는
오늘 리포트에 아직 해당 섹션이 없으므로 `pending`(데이터 파일은 있으니 "데이터 확인 완료 · 분석
대기 중") 또는 리포트에 아직 이 섹션들이 없다면 raw_data_glob이 있는 trigger는 pending, raw_data_glob이
없는 maverick/guardian/balance는 `pending`(대기 중)으로 나온다. `locked`는 더 이상 나오지 않는다.

- [ ] **Step 3: Commit**

```bash
git add scripts/office_data.py
git commit -m "feat: 오피스 화면에서 Trigger/Maverick/Guardian/Balance 잠금 해제"
```

---

### Task 6: `.claude/agents/chief-strategist.md` — 리포트에 매매 시그널 섹션 반영

**Files:**
- Modify: `.claude/agents/chief-strategist.md`

**Interfaces:**
- Consumes: Task 1~4가 정의한 4개 서브에이전트의 출력 텍스트(오케스트레이터가 전달)
- Produces: `reports/YYYY-MM-DD.md`에 "## Trigger - 매매 시그널 생성" / "## Maverick - 공격적 리스크 검토" / "## Guardian - 보수적 리스크 검토" / "## Balance - 중립 리스크 검토" 4개 섹션 추가. Task 5의 `report_sections` 값과 정확히 일치해야 `office_data.py`가 파싱한다.

- [ ] **Step 1: 역할 설명에 크립토 매매 시그널 흐름 추가**

`.claude/agents/chief-strategist.md`의 아래 블록(현재 13~16줄, "크립토 데스크: Candle..." 줄 바로
다음)을 찾아서:

```markdown
- **크립토 데스크**: Candle(기술적분석), Proto(펀더멘털), Vibes(뉴스·심리) → Node(리서치 종합)
- **국내주식 데스크**: Chart(기술적분석), Ledger(펀더멘털), Mood(뉴스·심리) → Anchor(리서치 종합)
```

두 줄 사이에 아래 줄을 끼워 넣는다(크립토 데스크 줄과 국내주식 데스크 줄 사이):

```markdown
- **크립토 데스크**: Candle(기술적분석), Proto(펀더멘털), Vibes(뉴스·심리) → Node(리서치 종합)
  → Trigger(매매 시그널 생성) → Maverick/Guardian(리스크 검토) → Balance(최종 권고) *(2단계, 크립토 파일럿)*
- **국내주식 데스크**: Chart(기술적분석), Ledger(펀더멘털), Mood(뉴스·심리) → Anchor(리서치 종합)
```

- [ ] **Step 2: 리포트 템플릿에 4개 섹션 추가**

`## Node - 크립토 리서치 종합` 섹션(현재 57~58줄)과 `## Chart - 국내주식 기술적 분석` 섹션(현재
60줄) 사이에 아래 4개 섹션을 끼워 넣는다.

```markdown
## Trigger - 매매 시그널 생성
(trigger 결과 원문)

## Maverick - 공격적 리스크 검토
(maverick 결과 원문)

## Guardian - 보수적 리스크 검토
(guardian 결과 원문)

## Balance - 중립 리스크 검토
(balance 결과 원문)

```

- [ ] **Step 3: 매수/매도 시그널 금지 제약을 매매 시그널 섹션 예외로 수정**

`## 매우 중요한 제약사항` 아래 첫 두 줄(현재 95~96줄)을:

```markdown
- **이 리포트는 매수/매도 시그널이 아닙니다.** "지금 사세요/파세요" 같은 직접적 매매 지시나 확정적 추천을 하지 마세요.
- "관찰 포인트", "참고할 만한 흐름" 수준의 표현만 사용하세요. 구체적 매수/매도 시그널 생성은 2단계(향후 추가될 trading-strategist)에서 다룹니다.
```

아래로 교체한다:

```markdown
- **"오늘의 요약"·"주목할 리스크"·"참고 의견" 섹션은 매수/매도 시그널이 아닙니다.** "지금
  사세요/파세요" 같은 직접적 매매 지시나 확정적 추천을 하지 마세요 — "관찰 포인트", "참고할 만한
  흐름" 수준의 표현만 사용하세요.
- **구체적 매매 시그널은 Trigger/Maverick/Guardian/Balance 섹션(크립토 데스크, 2단계 파일럿)에서만
  다룹니다.** 이 섹션들의 원문은 그대로 옮기되, 그 외 섹션에서 새로 매매 시그널을 만들어내지
  마세요.
- **매매 시그널이라도 실제 주문 지시는 아닙니다.** 실제 주문은 사람이 거래소에서 직접 실행한다는
  전제를 유지하세요(각 담당 에이전트가 이미 명시했습니다).
```

- [ ] **Step 4: frontmatter 문법 검증 (파일이 여전히 유효한지만 확인)**

Run:
```
python -c "
import yaml
text = open('.claude/agents/chief-strategist.md', encoding='utf-8').read()
d = yaml.safe_load(text.split('---')[1])
print(d['name'], d['tools'])
assert 'Trigger - 매매 시그널 생성' in text
assert 'Balance - 중립 리스크 검토' in text
print('섹션 헤더 확인 OK')
"
```
Expected: `chief-strategist Read, Write, Glob` 출력 후 `섹션 헤더 확인 OK`.

- [ ] **Step 5: Commit**

```bash
git add .claude/agents/chief-strategist.md
git commit -m "feat: chief-strategist 리포트에 크립토 매매 시그널 섹션 반영"
```

---

### Task 7: `.claude/commands/daily-report.md` — 파이프라인에 매매 시그널 단계 추가

**Files:**
- Modify: `.claude/commands/daily-report.md`

**Interfaces:**
- Consumes: Task 1~4 에이전트 이름(`trigger`/`maverick`/`guardian`/`balance`)
- Produces: 없음(오케스트레이션 지시문 갱신)

- [ ] **Step 1: 3번(리서치팀) 다음에 매매 시그널 단계 삽입, 이후 번호 갱신**

`.claude/commands/daily-report.md`에서 아래 원문 블록(기존 4~7번 스텝)을 찾는다.

```markdown
4. **PM**: 2번의 9개 분석 결과와 3번의 리서치 종합 결과(node/anchor/compass 3개)를 `chief-strategist` 서브에이전트에게 전달해 최종 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성하게 합니다.

5. `python scripts\generate_office.py`를 실행해 최신 데이터/리포트를 반영한 `office\index.html`을 생성합니다.

6. `Start-Process "office\index.html"`로 시각적 AI 오피스를 기본 브라우저에서 자동으로 엽니다.

7. 완료되면 생성된 리포트 경로를 사용자에게 알리고, 리포트의 핵심 요약(오늘의 요약 섹션)을 대화창에 그대로 보여주세요.
```

이 블록을 통째로 아래로 교체한다.

```markdown
4. **크립토 매매 시그널 (2단계, 파일럿)**: 3번에서 나온 `node`의 리서치 종합 결과를 `trigger`에게
   전달해 코인별 진입가·목표가·손절가·포지션 크기를 생성합니다. 그 결과를 `maverick`과 `guardian`에게
   각각 전달해 병렬로 리스크 검토를 받습니다(둘은 서로 독립적이므로 병렬 호출 가능). 마지막으로
   `trigger`/`maverick`/`guardian` 결과를 모두 `balance`에게 전달해 최종 권고로 저울질합니다.
   국내주식/해외주식 데스크는 이 단계가 없습니다(크립토만 파일럿).

5. **PM**: 2번의 9개 분석 결과, 3번의 리서치 종합 결과(node/anchor/compass 3개), 4번의 크립토 매매
   시그널 결과(trigger/maverick/guardian/balance 4개)를 `chief-strategist` 서브에이전트에게 전달해
   최종 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성하게 합니다.

6. `python scripts\generate_office.py`를 실행해 최신 데이터/리포트를 반영한 `office\index.html`을 생성합니다.

7. `Start-Process "office\index.html"`로 시각적 AI 오피스를 기본 브라우저에서 자동으로 엽니다.

8. 완료되면 생성된 리포트 경로를 사용자에게 알리고, 리포트의 핵심 요약(오늘의 요약 섹션)을 대화창에 그대로 보여주세요.
```

- [ ] **Step 2: 내용 확인**

Run:
```
python -c "
text = open('.claude/commands/daily-report.md', encoding='utf-8').read()
assert 'trigger' in text and 'maverick' in text and 'guardian' in text and 'balance' in text
assert '8. 완료되면' in text
print('OK')
"
```
Expected: `OK` 출력(치환 누락 없이 4개 에이전트 이름과 마지막 8번 스텝이 모두 존재).

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/daily-report.md
git commit -m "feat: daily-report 파이프라인에 크립토 매매 시그널 단계 추가"
```

---

### Task 8: `.claude/commands/scheduled-analysis.md` — 동일하게 파이프라인 갱신

**Files:**
- Modify: `.claude/commands/scheduled-analysis.md`

**Interfaces:**
- Consumes: Task 1~4 에이전트 이름(`trigger`/`maverick`/`guardian`/`balance`)
- Produces: 없음(오케스트레이션 지시문 갱신)

- [ ] **Step 1: 3번(리서치팀) 다음에 매매 시그널 단계 삽입, 이후 번호 갱신**

`.claude/commands/scheduled-analysis.md`에서 아래 원문 블록(기존 4~6번 스텝)을 찾는다.

```markdown
4. **PM**: 2번의 9개 분석 결과와 3번의 리서치 종합 결과(node/anchor/compass 3개)를 `chief-strategist` 서브에이전트에게 전달해 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성(또는 갱신)하게 합니다.

5. `python scripts\generate_office.py`를 실행해 `office\index.html` 스냅샷도 최신 상태로 갱신합니다.

6. 브라우저는 열지 않습니다. 완료되면 생성/갱신된 리포트 경로와 핵심 요약을 짧게 출력하고 종료하세요.
   중간에 예산 문제로 일부만 완료했다면, 어디까지 완료했는지도 함께 출력하세요.
```

이 블록을 통째로 아래로 교체한다.

```markdown
4. **크립토 매매 시그널 (2단계, 파일럿)**: 3번에서 나온 `node`의 리서치 종합 결과를 `trigger`에게
   전달해 코인별 진입가·목표가·손절가·포지션 크기를 생성합니다. 그 결과를 `maverick`과 `guardian`에게
   각각 전달해 병렬로 리스크 검토를 받습니다(둘은 서로 독립적이므로 병렬 호출 가능). 마지막으로
   `trigger`/`maverick`/`guardian` 결과를 모두 `balance`에게 전달해 최종 권고로 저울질합니다.
   국내주식/해외주식 데스크는 이 단계가 없습니다(크립토만 파일럿).

5. **PM**: 2번의 9개 분석 결과와 3번의 리서치 종합 결과(node/anchor/compass 3개), 4번의 크립토 매매
   시그널 결과(trigger/maverick/guardian/balance 4개)를 `chief-strategist` 서브에이전트에게 전달해
   종합 리포트를 `reports/YYYY-MM-DD.md`로 작성(또는 갱신)하게 합니다.

6. `python scripts\generate_office.py`를 실행해 `office\index.html` 스냅샷도 최신 상태로 갱신합니다.

7. 브라우저는 열지 않습니다. 완료되면 생성/갱신된 리포트 경로와 핵심 요약을 짧게 출력하고 종료하세요.
   중간에 예산 문제로 일부만 완료했다면, 어디까지 완료했는지도 함께 출력하세요.
```

- [ ] **Step 2: 내용 확인**

Run:
```
python -c "
text = open('.claude/commands/scheduled-analysis.md', encoding='utf-8').read()
assert 'trigger' in text and 'maverick' in text and 'guardian' in text and 'balance' in text
assert '7. 브라우저는 열지 않습니다' in text
print('OK')
"
```
Expected: `OK` 출력.

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/scheduled-analysis.md
git commit -m "feat: scheduled-analysis 파이프라인에 크립토 매매 시그널 단계 추가"
```

---

### Task 9: `README.md` — 로드맵 2단계 재정의, 3단계 삭제

**Files:**
- Modify: `README.md:3`, `README.md:7-16`

**Interfaces:**
- Consumes: 없음
- Produces: 없음(문서 갱신)

- [ ] **Step 1: 3줄 "3단계로 나눠서" → "2단계로 나눠서"**

`README.md` 3번째 줄:
```markdown
PC 상에서 실행되는 AI 에이전트 기반 투자 지원 시스템입니다. 리스크를 낮추기 위해 3단계로 나눠서 구축합니다.
```
아래로 교체:
```markdown
PC 상에서 실행되는 AI 에이전트 기반 투자 지원 시스템입니다. 리스크를 낮추기 위해 2단계로 나눠서 구축합니다.
```

- [ ] **Step 2: 로드맵 블록(7~16줄) 교체 — 3단계 삭제, 2단계 재정의**

현재 7~16줄:
```markdown
- [x] **1단계 — 정보 수집 & 추천 리포트** (현재 단계)
  암호화폐(업비트/바이빗)·국내주식·해외주식 데이터를 수집하고, 자산군별 데스크(크립토/국내주식/해외주식)마다
  애널리스트 3명 + 리서치 종합 1명을 두고 PM이 종합하는 총 13명의 AI "직원"이 분석해 매일 참고용
  리포트를 생성합니다. 아직 매매 시그널이나 자동 주문은 없습니다.
- [ ] **2단계 — 매매 신호 생성 + 승인 후 실행**
  구체적인 매수/매도 시그널(가격·수량·근거)을 생성하는 `trading-strategist` 에이전트를 추가하고,
  사람이 승인한 경우에만 주문이 실행되는 흐름을 만듭니다.
- [ ] **3단계 — 완전 자동 매매**
  업비트/바이빗 등 거래소 API로 실제 주문을 자동 실행합니다. 리스크 한도, 킬스위치, 실행 로그/모니터링이
  갖춰진 뒤에 진행합니다.
```

아래로 교체:
```markdown
- [x] **1단계 — 정보 수집 & 추천 리포트** (완료)
  암호화폐(업비트/바이빗)·국내주식·해외주식 데이터를 수집하고, 자산군별 데스크(크립토/국내주식/해외주식)마다
  애널리스트 3명 + 리서치 종합 1명을 두고 PM이 종합하는 총 13명의 AI "직원"이 분석해 매일 참고용
  리포트를 생성합니다.
- [ ] **2단계 — 매매 시그널 생성 (크립토 파일럿)** (현재 단계)
  크립토 데스크에 한해 Trigger(시그널 생성)와 Maverick/Guardian/Balance(리스크 검토)가 코인별
  진입가·목표가·손절가·포지션 크기(총자본 대비 %)를 산출합니다. **실제 주문은 100% 사람이 거래소
  앱/사이트에서 직접 실행합니다 — AI나 스크립트가 거래소 API를 호출해 주문을 넣는 기능은 이
  프로젝트에 없습니다.** 검증 후 국내주식/해외주식 데스크로 확장할 계획입니다.
```

- [ ] **Step 3: 내용 확인**

Run:
```
python -c "
text = open('README.md', encoding='utf-8').read()
assert '3단계' not in text, '3단계 문구가 아직 남아있음'
assert '2단계로 나눠서' in text
assert 'Trigger(시그널 생성)' in text
print('OK')
"
```
Expected: `OK` 출력 (다른 곳에 남아있던 "3단계" 문구가 있다면 여기서 걸린다 — 있으면 같이 정리).

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: 로드맵을 2단계(매매 시그널 생성, 크립토 파일럿)로 재정의, 3단계 삭제"
```

---

### Task 10: 엔드투엔드 수동 검증 (LLM 호출 비용 발생 — 실행 전 사용자 확인 필요)

**Files:** 없음(검증 전용)

이 태스크는 실제 서브에이전트(Trigger/Maverick/Guardian/Balance 포함 13명)를 전부 호출하므로 Claude
API 비용이 발생한다. **실행 전에 사용자에게 "지금 `/daily-report`(또는 `/scheduled-analysis`)를
실행해 검증해도 될까요?"라고 확인을 받은 뒤에만 진행한다.**

- [ ] **Step 1: 사용자 승인 후 `/daily-report` 1회 실행**

승인을 받으면 `/daily-report`를 실행한다.

- [ ] **Step 2: 리포트에 매매 시그널 섹션 확인**

`reports/YYYY-MM-DD.md`(오늘 날짜)를 열어 아래 4개 헤더가 모두 존재하는지 확인한다.
- `## Trigger - 매매 시그널 생성`
- `## Maverick - 공격적 리스크 검토`
- `## Guardian - 보수적 리스크 검토`
- `## Balance - 중립 리스크 검토`

Balance 섹션에 코인별 최종 방향·진입가·목표가·손절가·포지션 크기(%)가 숫자로 채워져 있는지, 관망인
코인은 진입가/목표가/손절가가 "해당 없음"으로 처리됐는지 확인한다.

- [ ] **Step 3: 오피스 화면에서 잠금 해제 확인**

`office\index.html`을 열어(자동으로 열림) TRADING 존(Trigger)과 RISK MGMT 존(Maverick/Guardian/
Balance)이 더 이상 "준비 중" 잠금 상태가 아니라 다른 애널리스트 카드처럼 "✅ 완료" 상태로 보이는지
확인한다. 카드를 클릭해 각자의 분석 전문이 모달로 뜨는지 확인한다.

- [ ] **Step 4: 기존 3개 데스크 회귀 확인**

크립토/국내주식/해외주식 3개 데스크의 기존 9명 애널리스트 + node/anchor/compass 카드가 여전히
정상적으로(잠기지 않고) 표시되는지 확인한다 — 이번 변경이 국내주식/해외주식 데스크에 영향을 주지
않아야 한다.

- [ ] **Step 5: `git status`로 의도한 파일만 변경됐는지 확인**

Run: `git status --short`

Expected: 이 계획에서 커밋한 파일들(`.claude/agents/trigger.md`, `maverick.md`, `guardian.md`,
`balance.md`, `chief-strategist.md`, `.claude/commands/daily-report.md`, `scheduled-analysis.md`,
`scripts/office_data.py`, `README.md`) 외에 `reports/*.md`, `data/*.json`,
`office/index.html`(Step 1 실행으로 생성/갱신됨)만 추가로 나타나야 한다. 이 리포트/데이터 파일은
기존 컨벤션대로 커밋하지 않는다(watchlist-editor 계획과 동일하게 untracked로 남겨둔다).
