# 시간별 자동화 안정화 — 설계

## 배경 / 문제

`AI투자오피스-시간별분석` Windows 작업 스케줄러 작업이 매시간 `/hourly-analysis`(22개 에이전트 + PM
파이프라인 전체)를 호출하고 있었으나, 실질적으로 대부분 실패하고 있었다.

- `logs/` 30개 중 21개가 0바이트. `reports/`에는 2026-08-01, 2026-08-03 단 2개만 존재.
- 작업 스케줄러의 `ExecutionTimeLimit`이 20분(`PT20M`)으로 설정되어 있는데, 22명 에이전트(WebSearch 포함)
  + 데이터 수집 + PM 종합까지 도는 파이프라인은 20분보다 훨씬 오래 걸림 → 매 실행마다 강제 종료
  (`LastTaskResult: 3221225786`, STATUS_CONTROL_C_EXIT).
- `hourly_2026-08-04_20-21.log`에서는 예산($1) 소진을 이유로 에이전트가 작업을 멈추고 사용자에게 계속
  여부를 되물음 — `hourly-analysis.md`에 명시된 "무인 실행이니 스스로 멈춰서 확인 요청하면 안 된다"는
  지시를 위반. 실제로는 시간제한에 먼저 걸려 죽었을 가능성이 크지만, 예산 초과 자체도 잠재적 위반 경로.
- 로그 파일이 깨진 인코딩(UTF-16 추정)으로 저장되어 있어 디버깅이 어려움
  (`run_hourly.ps1`의 `*> $LogFile` 리다이렉션 방식이 원인으로 추정).
- `run_hourly.ps1`은 `--max-budget-usd 5`인데 README에는 "$1 상한"이라고 적혀 있어 문서와 실제 설정이 불일치.

## 방향

매시간 22명 전체를 돌리는 구조 자체가 시간/비용 제약과 맞지 않는다고 판단, 2단 스케줄로 재설계한다.

1. **경량 시간별 갱신** (매시간, 비용 $0, LLM 호출 없음) — 가격/지표만 갱신
2. **전체분석** (하루 3회, 회당 $3 예산 상한) — 기존 22명 + PM 파이프라인

## 아키텍처

### 1. 경량 시간별 갱신
- 새 스크립트 `scripts/run_price_update.ps1`: 기존 4개 fetch 스크립트
  (`fetch_crypto.py`/`fetch_stocks_kr.py`/`fetch_stocks_us.py`/`fetch_macro.py`) +
  `generate_office.py`를 순서대로 실행. Claude 호출 없음.
- Windows 작업 스케줄러의 기존 "AI투자오피스-시간별분석" 작업 액션을 이 스크립트로 교체. 트리거(매시간)는
  그대로 유지.
- LLM 호출이 없으므로 WebSearch 비용, 시간제한 초과 위험 모두 없음 (수 초~수십 초 내 종료).

### 2. 전체분석 (하루 3회)
- `.claude/commands/hourly-analysis.md`를 `.claude/commands/scheduled-analysis.md`로 이름 변경(내용은
  동일한 22명+PM 파이프라인 유지). 슬래시 커맨드 `/scheduled-analysis`로 변경.
- `scripts/run_hourly.ps1`을 `scripts/run_scheduled_analysis.ps1`로 이름 변경하고 다음을 수정:
  - `--max-budget-usd 5` → `--max-budget-usd 3`
  - 로그 저장 방식을 `*> $LogFile` → `... 2>&1 | Out-File -FilePath $LogFile -Encoding utf8`로 교체해
    UTF-8로 정상 저장되도록 수정
- 새 Windows 작업 스케줄러 작업 등록: 이름 "AI투자오피스-전체분석", 트리거 3개 — 09:00(국내장 시작) /
  16:00(국내장 마감·미국장 프리마켓) / 23:30(미국장 개장 직후), 액션은
  `run_scheduled_analysis.ps1` 호출.
- `ExecutionTimeLimit`을 20분 → 55분(`PT55M`)으로 상향해 하루 3회 실행 중 강제 종료되지 않도록 함.

### 3. 문서/지시문 수정
- `scheduled-analysis.md`(구 hourly-analysis.md)에 예산 상한에 도달했을 때도 되묻지 않고 그 시점까지의
  결과로 조용히 종료하도록 문구 보강.
- README의 자동화 관련 섹션(스케줄, 명령어, 예산, 로그 경로)을 새 구조에 맞게 갱신.

## 에러 처리
- 경량 갱신 스크립트: 개별 fetch 실패 시 다음 fetch로 계속 진행(기존 `serve_office.py`의
  `price_update_loop`와 동일한 try/except 패턴을 참고). 전체가 멈추지 않아야 함.
- 전체분석: 예산 상한 도달 시 진행된 결과만으로 조용히 종료(사용자에게 되묻지 않음). 시간제한(55분) 도달
  시에도 마찬가지로 강제 종료되지만, 정상 케이스에서는 여유 내에 끝나는 것을 목표로 함.

## 테스트/검증
자동 테스트 프레임워크는 두지 않고, 변경 후 수동 1회 실행으로 확인한다.
- `run_price_update.ps1` 실행 → `data/*` 최신 파일 생성 + `office/index.html` 갱신 확인
- `run_scheduled_analysis.ps1` 실행 → 로그가 UTF-8로 정상적으로 읽히는지, `reports/오늘날짜.md`가 끝까지
  생성되는지 확인

## 범위 밖 (다음에)
- 리포트/분석 내용 자체의 품질 개선, 에이전트 구성 변경
- 코드베이스 구조 리팩터링
- 2단계(매매 시그널) 기능 추가

사용자 요청: "우선 진행하고 나중에 더 기능을 추가해보자" — 위 범위 밖 항목들은 이번 작업에 포함하지 않는다.
