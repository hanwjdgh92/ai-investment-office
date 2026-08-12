# 크립토 Bull/Bear 토론 분리 + Trigger 시그널 JSON 구조화 Design Spec

**작성일:** 2026-08-12
**배경:** TradingAgents(TauricResearch) 오픈소스 멀티에이전트 트레이딩 프레임워크 분석 결과, 이
프로젝트와 겹치는 구조가 많았다. 그중 두 가지가 실제로 적용할 가치가 있다고 판단해 이번 spec으로
정리한다.
1. TradingAgents는 Bull/Bear 리서처가 실제로 라운드를 주고받으며 반박한 뒤 Research Manager가
   심판하는 구조인데, 이 프로젝트의 Node는 혼자 강세/약세 논거를 둘 다 세우고 스스로 저울질한다 —
   진짜 반박이 아니라 자기 시뮬레이션이다.
2. TradingAgents는 Trader/Portfolio Manager 출력을 Pydantic 스키마로 강제해 기계적으로 파싱
   가능하지만, 이 프로젝트는 `office_data.py`가 "SYMBOL:" 줄 접두어 정규식(`match_symbol_lines`)에만
   의존해 종목별 데이터를 재구성한다.

## 결정 사항

- **Bull/Bear 분리는 크립토 데스크만 적용한다.** 국내주식(Anchor)·해외주식(Compass)은 이번 범위
  밖 — 크립토 매매 시그널(Trigger/Maverick/Guardian/Balance)이 크립토만 파일럿이었던 것과 같은
  이유로, 검증 전에 세 데스크 모두 바꾸지 않는다.
- **토론은 1라운드.** Bull이 강세 논거를 먼저 쓰고, Bear가 그 글을 읽고 약세 논거+반박을 쓴다.
  Bull의 재반박(2라운드)은 넣지 않는다 — 에이전트 호출 횟수·시간·비용 대비 이득이 크지 않다고
  판단.
- **Node는 심판 역할만 남긴다.** 지금처럼 스스로 강세/약세를 둘 다 쓰지 않고, Bull/Bear가 이미
  작성한 논거를 받아 저울질(근거 품질 비교·비대칭성 평가·지켜볼 지점)만 한다.
- **Trigger 시그널은 JSON 블록으로도 병행 출력한다.** 기존 마크다운 출력은 그대로 유지하고 그 뒤에
  fenced JSON 블록을 추가한다. `office_data.py`가 이를 파싱해 watchlist 카드에 `signal` 필드로
  붙인다.
- **이번 범위는 데이터 구조화까지만.** office UI(배지 색상, 포지션%순 정렬, 방향 필터)는 이번에
  만들지 않는다 — 필드는 준비해두고 화면 작업은 필요해지면 별도 spec으로 진행한다.

## 목표

- Bear가 Bull의 실제 문장을 인용해 반박하는, 진짜 두 에이전트 간 토론을 파이프라인에 도입해
  크립토 리서치 판단의 품질(특히 근거 비대칭성 평가)을 개선한다.
- Trigger가 산출한 코인별 방향·진입가·목표가·손절가·포지션%를 기계가 파싱 가능한 형태로도
  남겨, 이후 오피스 UI가 텍스트 정규식 없이 구조화된 데이터를 활용할 수 있게 준비한다.

## 범위 밖 (Non-goals)

- 국내주식/해외주식 데스크에 Bull/Bear 패턴 확장 — 크립토 검증 후 별도 spec.
- 2라운드 이상 토론, 토론 라운드 수 설정 옵션화.
- office UI에서 signal 필드를 실제로 시각화(배지/정렬/필터) — 데이터만 준비.
- 시그널 이력 추적, 백테스트, 알림 — 기존 spec들과 동일하게 계속 범위 밖.
- Node 외 다른 에이전트(Anchor/Compass/Maverick/Guardian/Balance 등)의 프롬프트나 출력 형식 변경.

## 아키텍처

### 1. 크립토 리서치 파이프라인 변경

```
Candle/Proto/Vibes (기존, 병렬 분석)
  → Bull (신규): 3명의 분석 결과에서 코인별 강세 논거(핵심 촉매·근거 강도)만 정리
  → Bear (신규): 3명의 분석 결과 + Bull의 강세 논거를 받아 약세 논거를 정리하고,
    Bull이 든 근거 중 약하거나 과장된 부분을 구체적으로 반박
  → Node (기존, 역할 축소): Bull/Bear의 논거를 받아 저울질만 함
    (근거 품질 비교 → 비대칭성 평가 → 지켜볼 지점) — 스스로 강세/약세를 새로 쓰지 않음
  → Trigger (기존, 변경 없음)
```

국내주식(Chart/Ledger/Mood → Anchor)·해외주식(Trend/Vault/Pulse → Compass) 파이프라인은
변경하지 않는다.

### 2. 신규 에이전트

**`.claude/agents/bull.md`** (tools: Read)
- 입력: Candle/Proto/Vibes 오늘자 분석 텍스트.
- 역할: 코인별로 강세(상승) 쪽으로 해석 가능한 근거만 정리 — 핵심 촉매 1~2개, 근거 강도(몇 명의
  애널리스트 데이터가 겹치는지, 사실/해석 구분). 기존 `node.md`의 "1. 강세 논거 세우기" 섹션
  내용을 그대로 옮겨온다.
- 약세 논거를 의식해 미리 타협하지 않고 최대한 설득력 있게 세운다.

**`.claude/agents/bear.md`** (tools: Read)
- 입력: Candle/Proto/Vibes 오늘자 분석 텍스트 + Bull의 출력.
- 역할: 코인별로 약세(하락/리스크) 쪽 근거를 정리(기존 node.md "2. 약세 논거 세우기"와 동일 기준).
  추가로 Bull이 제시한 근거 중 약한 근거(해석에 불과하거나 애널리스트 1명 데이터에만 의존하는 것
  등)를 구체적으로 짚어 반박하는 섹션을 별도로 둔다.
- Bull의 주장을 왜곡하거나 과장해서 반박하지 않는다 — Bull이 실제로 쓴 내용만 인용한다.

### 3. Node 프롬프트 변경

`node.md`에서 "1. 강세 논거 세우기" / "2. 약세 논거 세우기" 섹션을 삭제하고, 입력 설명을
"Candle/Proto/Vibes 분석"에서 "Bull의 강세 논거 + Bear의 약세 논거·반박"으로 교체한다. "3. 저울질
(종합)" 섹션은 그대로 유지하되, 저울질 대상이 "내가 쓴 강세/약세"가 아니라 "Bull/Bear가 각각 쓴
강세/약세"로 바뀐다. 출력 형식과 주의사항(매수/매도 추천 안 함 등)은 변경 없음.

### 4. 파이프라인 문서 변경

`.claude/commands/daily-report.md`, `.claude/commands/scheduled-analysis.md`의 3번 단계 중
크립토 부분을:
```
크립토 데스크: candle/proto/vibes 결과 → bull에게 전달해 강세 논거 작성
  → bull 결과를 bear에게 전달해 약세 논거+반박 작성 → bull/bear 결과 모두 node에게 전달해 저울질
```
로 교체한다(순차 호출 — bear는 bull 출력이 있어야 반박 가능). 국내주식/해외주식 줄은 그대로 두고,
"세 데스크는 서로 독립적이므로 병렬 호출 가능"이라는 문구는 "데스크 간에는 병렬, 크립토 데스크
내부(bull→bear→node)는 순차"로 명확히 한다.

### 5. 오피스 UI 카드 추가 (Bull/Bear만, 표시 방식은 기존 패턴 재사용)

`scripts/office_data.py`의 `EMPLOYEES`에 bull/bear 항목을 node 앞에 추가한다(team: "크립토",
subteam: "RESEARCH", report_sections: 각각 `["Bull - 크립토 강세 논거"]` /
`["Bear - 크립토 약세 논거"]`). 새 파싱 로직은 불필요 — 기존 `parse_report_sections`가 헤더
기준으로 그대로 처리한다.

`chief-strategist.md`의 리포트 템플릿에 `## Bull - 크립토 강세 논거`, `## Bear - 크립토 약세
논거` 헤더를 Vibes 섹션과 Node 섹션 사이에 추가한다.

### 6. Trigger 시그널 JSON 구조화

`trigger.md` 출력 형식 섹션에 기존 마크다운 뒤 fenced JSON 블록을 추가로 출력하도록 지시를 붙인다:
```json
{"signals":[
  {"symbol":"ETH","direction":"buy","entry":2702000,"target":2727000,"stop":2699200,"position_pct":3,"rr":8.9},
  {"symbol":"BTC","direction":"hold","entry":null,"target":null,"stop":null,"position_pct":0,"rr":null}
]}
```
- `direction`: `"buy"` / `"sell"` / `"hold"` 셋 중 하나.
- `hold`일 때 entry/target/stop/rr은 `null`, position_pct는 `0`.
- `symbol`은 watchlist 매칭에 쓰는 심볼(예: BTC, ETH)과 동일하게 맞춘다.

`scripts/office_data.py`에 `parse_json_block(text: str) -> dict | None` 추가: Trigger 섹션
텍스트에서 ```json ... ``` 블록을 정규식/문자열 탐색으로 찾아 `json.loads`. 실패하거나 블록이
없으면 `None`을 반환하고 기존 텍스트 기반 표시만 사용(에러를 던지지 않음). 성공 시 `signals`
리스트를 심볼별 dict로 변환해, watchlist 카드 생성 로직(`build_office_data`)에서 크립토
watchlist item에 `signal` 필드로 병합한다. `office/index.html`(JS)은 이번 범위에서 이 필드를
사용하지 않는다 — 데이터만 준비.

## 에러 처리

- Bear가 Bull 결과를 받지 못하면(Bull 실패) 기존 파이프라인 에러 처리 패턴을 따른다 — 실패한
  자리는 에러 문구 카드로 표시하고 나머지는 계속 진행한다.
- Trigger의 JSON 블록이 마크다운 형식과 어긋나거나 빠져 있어도 리포트 생성이나 오피스 갱신은
  절대 실패하지 않는다 — `signal` 필드가 비는 것으로 그친다.

## 검증

이 저장소는 자동 테스트 프레임워크가 없다(기존 컨벤션과 동일). `/daily-report` 1회 실행 후
육안으로 확인한다.
- `reports/YYYY-MM-DD.md`에 "Bull - 크립토 강세 논거", "Bear - 크립토 약세 논거" 섹션이 생기고,
  Bear 섹션이 Bull의 실제 문장을 인용해 반박하는지.
- Node 섹션이 더 이상 "1. 강세 논거"/"2. 약세 논거"를 자체 생성하지 않고 Bull/Bear 인용 기반
  저울질만 하는지.
- 오피스 UI(office/index.html)에서 크립토 RESEARCH 존에 Bull/Bear 카드가 Node 앞에 보이는지.
- Trigger 섹션 원문에 fenced JSON 블록이 포함돼 있는지, `python scripts\generate_office.py`
  실행이 에러 없이 끝나는지(JSON 파싱 실패 시에도 스크립트가 죽지 않는지).
