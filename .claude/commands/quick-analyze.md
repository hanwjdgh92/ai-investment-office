---
description: 워치리스트에 없는 종목 하나를 즉석으로 조회해 AI가 분석한다. 인자 "<type> <symbol>" (type은 crypto/stocks_kr/stocks_us). data/adhoc/에 임시 데이터만 만들고 reports/나 watchlist에는 남기지 않는다.
---

인자 `$ARGUMENTS`를 공백 기준으로 앞의 두 값만 취해 `type`과 `symbol`로 나누세요 (예: "crypto BTC" →
type=crypto, symbol=BTC). type은 반드시 crypto/stocks_kr/stocks_us 중 하나입니다.

1. PowerShell로 아래 명령을 실행해 이 종목 하나만 조회한 데이터를 `data/adhoc/<type>_<symbol 대문자>.json`에
   저장합니다.
   - `python scripts\fetch_adhoc.py <type> <symbol>`
   (python이 PATH에 없다면 `$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")` 를 먼저 실행)
   - 이 명령이 실패하면(에러 출력 또는 0이 아닌 종료코드) 즉시 중단하고 "조회 실패: <에러 메시지>"만
     출력한 뒤 종료하세요. 이후 서브에이전트 호출 단계는 진행하지 않습니다.

2. type에 따라 아래 서브에이전트들을 호출합니다. 이때 각 애널리스트에게 "오늘자 워치리스트 데이터 파일
   (`data/crypto_YYYY-MM-DD.json` 등) 대신 `data/adhoc/<type>_<symbol>.json` 파일 하나만 읽고, 그 안의
   종목 하나만 분석하라"고 명시적으로 지시하세요.

   - **crypto**: `candle`/`proto`/`vibes`를 병렬로 호출 → 세 결과를 `node`에게 전달해 리서치 종합 →
     `node` 결과를 `trigger`에게 전달해 매매 시그널 생성 → `trigger` 결과를 `maverick`/`guardian`에게
     각각 병렬로 전달해 리스크 검토 → `trigger`/`maverick`/`guardian` 결과를 모두 `balance`에게 전달해
     최종 권고로 종합.
   - **stocks_kr**: `chart`/`ledger`/`mood`를 병렬로 호출 → 세 결과를 `anchor`에게 전달해 리서치 종합.
   - **stocks_us**: `trend`/`vault`/`pulse`를 병렬로 호출 → 세 결과를 `compass`에게 전달해 리서치 종합.

3. 아래 형식으로 최종 결과를 대화창에 그대로 출력하세요. **`reports/`에 파일로 쓰지 말고,
   `config/watchlist.yaml`에도 추가하지 마세요.**

   ```
   # <symbol> 즉시분석

   ## <애널리스트1 닉네임> - <역할>
   (해당 애널리스트 출력 그대로)

   ## <애널리스트2 닉네임> - <역할>
   ...

   ## <애널리스트3 닉네임> - <역할>
   ...

   ## <리서치종합 담당 닉네임> - 리서치 종합
   ...
   ```

   crypto인 경우에만 그 아래 이어서:
   ```
   ## Trigger - 매매 시그널
   ...
   ## Maverick - 공격적 리스크 검토
   ...
   ## Guardian - 보수적 리스크 검토
   ...
   ## Balance - 최종 권고
   ...
   ```

`data/adhoc/<type>_<symbol>.json` 정리는 이 커맨드가 하지 않습니다. 이 커맨드를 헤드리스로 호출하는
`scripts/run_quick_analyze.ps1`이 실행 후 항상 삭제하므로(Claude 권한 승인 없이 동작), 여기서는
3번까지만 하고 종료하세요.
