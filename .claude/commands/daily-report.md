---
description: 암호화폐/국내주식/해외주식 데이터를 수집하고 애널리스트팀·리서치팀·PM(The Boss)이 분석한 오늘의 투자 리포트를 생성한 뒤, 시각적 AI 오피스를 열어 보여준다.
---

다음 순서로 오늘의 투자 리포트를 생성하세요.

1. PowerShell로 아래 4개 스크립트를 순서대로 실행해 `data/` 폴더에 오늘 날짜의 원시 데이터(가격·기술적 지표·
   펀더멘털·매크로 지표)를 생성합니다.
   - `python scripts\fetch_crypto.py`
   - `python scripts\fetch_stocks_kr.py`
   - `python scripts\fetch_stocks_us.py`
   - `python scripts\fetch_macro.py`
   (python이 PATH에 없다면 `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` 를 먼저 실행)

2. **애널리스트팀**: 아래 9개 서브에이전트를 호출해 오늘 데이터를 분석하게 합니다. 모두 서로 독립적이므로 병렬로 호출하세요.
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

5. **PM**: 2번의 9개 분석 결과, 3번의 리서치 종합 결과(bull/bear/node/anchor/compass 5개), 4번의 크립토
   매매 시그널 결과(trigger/maverick/guardian/balance 4개)를 `chief-strategist` 서브에이전트에게 전달해
   최종 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성하게 합니다.

6. `python scripts\generate_office.py`를 실행해 최신 데이터/리포트를 반영한 `office\index.html`을 생성합니다.

7. `Start-Process "office\index.html"`로 시각적 AI 오피스를 기본 브라우저에서 자동으로 엽니다.

8. 완료되면 생성된 리포트 경로를 사용자에게 알리고, 리포트의 핵심 요약(오늘의 요약 섹션)을 대화창에 그대로 보여주세요.
