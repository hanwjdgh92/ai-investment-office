---
description: (자동화용) 데이터 수집 + 애널리스트팀·리서치팀·PM 분석 + 리포트 작성 + 오피스 갱신. 브라우저는 열지 않는다. Windows 작업 스케줄러가 시간별로 호출한다.
---

`/daily-report`와 동일하지만, 무인 실행이므로 브라우저를 열지 않습니다. 무인 실행이라 답할 사람이 없으므로,
예산이나 진행 여부를 되묻지 말고 끝까지 진행하세요 (예산이 정말 부족해 중단되는 것은 괜찮지만, 스스로 멈춰서
확인을 요청하면 안 됩니다). 다음 순서로 진행하세요.

1. PowerShell로 아래 4개 스크립트를 순서대로 실행해 `data/` 폴더에 최신 원시 데이터(가격·기술적 지표·펀더멘털·
   매크로 지표)를 생성합니다.
   - `python scripts\fetch_crypto.py`
   - `python scripts\fetch_stocks_kr.py`
   - `python scripts\fetch_stocks_us.py`
   - `python scripts\fetch_macro.py`

2. **애널리스트팀**: 아래 12개 서브에이전트를 병렬로 호출해 최신 데이터를 분석하게 합니다.
   - 크립토 데스크: `candle`, `vibes`, `chain`, `proto`
   - 국내주식 데스크: `chart`, `scoop`, `mood`, `ledger`
   - 해외주식 데스크: `trend`, `herald`, `pulse`, `vault`

3. **리서치팀 (데스크별 독립 진행)**: 세 데스크 모두 독립적이므로 한꺼번에 병렬로 호출해도 됩니다.
   - 크립토 데스크: `ape`(강세)·`fud`(약세) 병렬 호출 → `node`에게 전달해 종합
   - 국내주식 데스크: `rally`(강세)·`slump`(약세) 병렬 호출 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `surge`(강세)·`drag`(약세) 병렬 호출 → `compass`에게 전달해 종합

4. **PM**: 2번의 12개 분석 결과와 3번의 데스크별 리서치 결과(ape/fud/node, rally/slump/anchor, surge/drag/compass 9개)를 `chief-strategist` 서브에이전트에게 전달해 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성(또는 갱신)하게 합니다.

5. `python scripts\generate_office.py`를 실행해 `office\index.html` 스냅샷도 최신 상태로 갱신합니다.

6. 브라우저는 열지 않습니다. 완료되면 생성/갱신된 리포트 경로와 핵심 요약을 짧게 출력하고 종료하세요.
