# AI 투자 오피스

PC 상에서 실행되는 AI 에이전트 기반 투자 지원 시스템입니다. 리스크를 낮추기 위해 3단계로 나눠서 구축합니다.

## 진행 단계

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

## 구성 ("AI 직원")

애널리스트팀은 자산군(암호화폐/국내주식/해외주식)별로 나뉘고, 각 자산군 안에서 다시 기술적분석/펀더멘털/
뉴스·심리 3가지 관점으로 분석을 나눠 맡습니다. 데스크별 리서치 종합 담당(Node/Anchor/Compass)이 강세·
약세 논거를 스스로 세운 뒤 저울질해 리서치 노트로 정리합니다.

| 팀 | 이름 | 역할 | 파일 |
|---|---|---|---|
| ANALYSTS(크립토) | Candle | 암호화폐 기술적 분석 | `.claude/agents/candle.md` |
| ANALYSTS(크립토) | Proto | 암호화폐 펀더멘털 | `.claude/agents/proto.md` |
| ANALYSTS(크립토) | Vibes | 암호화폐 뉴스·심리 | `.claude/agents/vibes.md` |
| RESEARCH(크립토) | Node | 크립토 리서치 종합 | `.claude/agents/node.md` |
| ANALYSTS(국내주식) | Chart | 국내주식 기술적 분석 | `.claude/agents/chart.md` |
| ANALYSTS(국내주식) | Ledger | 국내주식 펀더멘털 | `.claude/agents/ledger.md` |
| ANALYSTS(국내주식) | Mood | 국내주식 뉴스·심리 | `.claude/agents/mood.md` |
| RESEARCH(국내주식) | Anchor | 국내주식 리서치 종합 | `.claude/agents/anchor.md` |
| ANALYSTS(해외주식) | Trend | 해외주식 기술적 분석 | `.claude/agents/trend.md` |
| ANALYSTS(해외주식) | Vault | 해외주식 펀더멘털 | `.claude/agents/vault.md` |
| ANALYSTS(해외주식) | Pulse | 해외주식 뉴스·심리 | `.claude/agents/pulse.md` |
| RESEARCH(해외주식) | Compass | 해외주식 리서치 종합 | `.claude/agents/compass.md` |
| PM OFFICE | The Boss | 종합 리포트 작성 (포트폴리오 매니저) | `.claude/agents/chief-strategist.md` |

TRADING(Trigger)·RISK MGMT(Maverick/Guardian/Balance) 팀은 오피스 화면에 자리만 마련되어 있고, 2단계(매매
시그널)·3단계(자동매매·리스크 한도)가 실제로 구축되면 합류합니다.

데이터 수집(가격/거래량 등 정확한 숫자)은 Python 스크립트가 담당하고, 뉴스 해석·요약·종합 판단은
Claude Code 서브에이전트가 담당합니다. 숫자는 코드로, 판단은 AI로 — 라는 원칙입니다.

수집하는 데이터는 다음과 같습니다.
- **가격/거래량**: 업비트·바이빗(암호화폐), FinanceDataReader(국내), yfinance(해외)
- **기술적 지표**: 이동평균(MA5/20/60), RSI14 — `scripts/indicators.py`에서 계산 (자산군 공용)
- **펀더멘털**: PER/PBR (국내는 네이버 금융, 해외는 yfinance), 해외는 시가총액·52주 최고/최저 포함
- **매크로 지표**: 원/달러 환율, 코스피, S&P500, 미국 10년물 금리, 달러 인덱스 (`scripts/fetch_macro.py`)

## 사용법

### 1. 관심 종목/코인 수정
`config/watchlist.yaml` 파일을 열어 자유롭게 추가/삭제하세요. 현재는 예시로 소수만 등록되어 있습니다.
- 암호화폐: BTC, ETH
- 국내 주식: 삼성전자, SK하이닉스
- 해외 주식: Apple, NVIDIA

### 2. 리포트 생성
Claude Code에서 이 폴더를 열고 아래 명령을 실행하세요.

```
/daily-report
```

데이터 수집 → 애널리스트 분석 → 종합 리포트 → 시각적 AI 오피스 생성 순으로 자동 진행되며,
리포트는 `reports/YYYY-MM-DD.md`에 저장되고 마지막에 `office/index.html`이 브라우저로 자동 열립니다.

### 바탕화면 아이콘
바탕화면에 아래 두 개가 만들어져 있어 명령어 없이 더블클릭만으로 실행할 수 있습니다.
- **AI 투자 오피스** — 가장 최근 스냅샷(`office/index.html`)을 바로 엽니다.
- **AI 투자 오피스 (실시간)** — `launch_live_office.bat`을 실행해 라이브 가격 뷰어(`serve_office.py`)를 띄우고 브라우저를 자동으로 엽니다. 검은 창이 뜨는데, 그게 서버이니 끄려면 그 창을 닫으면 됩니다.

### 3. 시각적 AI 오피스 (스냅샷 보기)
`office/index.html`을 더블클릭하면 언제든 다시 열어볼 수 있습니다. AI 직원들이 팀 구역("방")에 있는 모습과,
직원들이 올린 분석 내용이 쌓이는 "대표 콘솔" 피드를 볼 수 있습니다.
- 방 카드를 클릭하면 해당 직원의 오늘 분석 전문을 볼 수 있습니다.
- `/daily-report`나 자동 실행(시간별 갱신·전체분석)이 끝날 때마다 그 시점의 최신 데이터로 다시 생성됩니다.
- 개인 투자 데이터가 담겨 있으므로 이 파일은 외부(claude.ai 등)에 게시하지 않고 로컬에만 둡니다.

### 4. 실시간으로 보기 (가격만, 비용 없음)
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python scripts\serve_office.py
```
`http://127.0.0.1:8787`가 자동으로 열리고, 이후부터는 암호화폐 30초·주식 2분 간격으로 가격이 계속 갱신됩니다.
LLM을 호출하지 않으므로 API 비용이 발생하지 않습니다. 종료하려면 터미널에서 Ctrl+C. 전체분석(아래, 하루 3회)이
새 리포트를 쓰면, 열어둔 페이지가 다음 폴링 때(최대 30초 이내) 그 내용을 자동으로 반영합니다.

### 5. 자동 실행 (Windows 작업 스케줄러, 비용 발생)
두 개의 작업이 등록되어 있습니다.

- **"AI투자오피스-시간별분석"** (매시간, 비용 없음): `scripts\run_price_update.ps1`을 실행해 가격/지표
  데이터만 갱신하고 `office\index.html` 스냅샷을 새로 만듭니다. LLM을 호출하지 않으므로 API 비용이
  발생하지 않습니다.
- **"AI투자오피스-전체분석"** (하루 3회 — 09:00/16:00/23:30, 비용 발생): `scripts\run_scheduled_analysis.ps1`이
  `claude -p "/scheduled-analysis"`를 무인으로 실행해 데이터 수집 → 애널리스트 분석 → 리포트 작성 →
  오피스 스냅샷 갱신까지 자동으로 수행합니다(브라우저는 열지 않음). **회당 최대 $3**로 예산 상한을
  걸어뒀습니다(`--max-budget-usd 3`, 하루 최대 $9).

- 등록 확인: `Get-ScheduledTask -TaskName "AI투자오피스-시간별분석"`, `Get-ScheduledTask -TaskName "AI투자오피스-전체분석"`
- 끄기: `Unregister-ScheduledTask -TaskName "AI투자오피스-시간별분석" -Confirm:$false` (전체분석도 태스크
  이름만 바꿔서 동일하게 실행하면 끌 수 있습니다)
- 로그 확인: 전체분석은 `logs\scheduled_YYYY-MM-DD_HH-mm.log` (UTF-8로 저장되어 바로 읽을 수 있습니다)
- 실행에 필요한 권한(PowerShell 스크립트 실행, 리포트/오피스 파일 쓰기, 서브에이전트 호출, 웹서치)은
  이 프로젝트 폴더 전용 `.claude/settings.local.json`에만 허용해뒀습니다(다른 프로젝트에는 영향 없음).

### 6. 스크립트 단독 실행 (디버깅용)
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
python scripts\fetch_crypto.py
python scripts\fetch_stocks_kr.py
python scripts\fetch_stocks_us.py
python scripts\fetch_macro.py
python scripts\generate_office.py
```

## 리포트 수신 방식
현재는 로컬 Markdown 파일(`reports/`)과 로컬 웹페이지(오피스)로만 확인합니다. 이메일/슬랙/텔레그램 등 다른
채널로 받고 싶은 방식이 정해지면 추가 연동을 진행할 수 있습니다.

## 주의사항
- 1단계 리포트는 참고용 정보 제공입니다. 매수/매도 지시가 아니며, 실제 투자 판단과 책임은 본인에게 있습니다.
- 암호화폐/주식 시세 데이터는 무료 공개 API/라이브러리(업비트·바이빗 공개 API, FinanceDataReader, yfinance)를
  사용하므로 지연이나 일시적 오류가 있을 수 있습니다.
- 자동 실행(시간별 갱신·전체분석)은 PC가 켜져 있고 로그인되어 있을 때만 동작합니다. 비용이 부담되면 전체분석 작업을 위 명령으로 끌 수 있습니다.
