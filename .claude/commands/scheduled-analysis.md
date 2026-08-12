---
description: (자동화용) 데이터 수집 + 애널리스트팀·리서치팀·PM 분석 + 리포트 작성 + 오피스 갱신. 브라우저는 열지 않는다. Windows 작업 스케줄러가 하루 3회(장 시작/중간/마감) 호출한다.
---

`/daily-report`와 동일하지만, 무인 실행이므로 브라우저를 열지 않습니다. 무인 실행이라 답할 사람이 없으므로,
예산이나 진행 여부를 사용자에게 되묻지 마세요. 특히 다음 두 경우 모두 "계속할까요?"처럼 확인을 요청하며
멈추지 말고, 그 시점까지 만든 결과만으로 조용히 마무리하고 종료하세요.
- 예산 상한(`--max-budget-usd`)에 도달해 더 이상 진행할 수 없을 때
- 남은 예산으로 남은 단계(애널리스트/리서치/PM)를 다 마치기 어려워 보일 때 — 이 경우도 스스로 판단해
  중단할지 계속할지 정하고, 사용자에게 묻지 않습니다.

다음 순서로 진행하세요.

1. PowerShell로 아래 4개 스크립트를 순서대로 실행해 `data/` 폴더에 최신 원시 데이터(가격·기술적 지표·펀더멘털·
   매크로 지표)를 생성합니다.
   - `python scripts\fetch_crypto.py`
   - `python scripts\fetch_stocks_kr.py`
   - `python scripts\fetch_stocks_us.py`
   - `python scripts\fetch_macro.py`

2. **애널리스트팀**: 아래 9개 서브에이전트를 병렬로 호출해 최신 데이터를 분석하게 합니다.
   - 크립토 데스크: `candle`, `proto`, `vibes`
   - 국내주식 데스크: `chart`, `ledger`, `mood`
   - 해외주식 데스크: `trend`, `vault`, `pulse`

3. **리서치팀 (데스크별 독립 진행)**: 데스크 간에는 서로 완전히 독립적이므로 병렬로 진행해도
   됩니다. 단 크립토 데스크는 내부적으로 순차 호출이 필요합니다(Bear가 Bull의 글을 읽고 반박해야
   하므로).
   - 크립토 데스크(순차): `candle`/`proto`/`vibes` 결과 → `bull`에게 전달해 강세 논거 작성 →
     `bull`의 결과를 `bear`에게 전달해 약세 논거+반박 작성 → `bull`/`bear` 결과를 모두 `node`에게
     전달해 저울질
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합

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
