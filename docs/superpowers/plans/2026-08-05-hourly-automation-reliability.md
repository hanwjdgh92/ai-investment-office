# 시간별 자동화 안정화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매시간 22명(현재는 13명) 전체 파이프라인을 돌리려다 20분 실행시간 제한에 걸려 강제 종료되던
문제를 해결한다. 경량 시간별 갱신(가격만, $0)과 하루 3회 전체분석(회당 $3, 55분 제한)의 2단 스케줄로
재구성한다.

**Architecture:** Windows 작업 스케줄러 작업을 2개로 재구성한다 — 기존 "AI투자오피스-시간별분석"은
경량 가격 갱신 스크립트로 액션을 교체하고, 새 "AI투자오피스-전체분석" 작업을 하루 3회 트리거로 등록해
전체 에이전트 파이프라인을 실행한다.

**Tech Stack:** PowerShell 스크립트, Windows 작업 스케줄러(`ScheduledTasks` 모듈), Claude Code 슬래시
커맨드.

## Global Constraints

- 참조 스펙: `docs/superpowers/specs/2026-08-05-hourly-automation-reliability-design.md`
- **선행 조건**: `docs/superpowers/plans/2026-08-05-agent-roster-consolidation.md`가 먼저 완료되어
  있어야 한다. 이 계획은 `.claude/commands/hourly-analysis.md`가 이미 9개 애널리스트 + 3개 리서치
  종합(node/anchor/compass) 구조로 갱신되어 있다고 가정한다.
- 이 프로젝트는 git 저장소가 아니므로 커밋 단계는 생략한다.
- 자동 테스트 프레임워크가 없으므로 각 태스크는 수동 실행으로 검증한다.
- 무인 실행 중 예산·시간 문제로 중단되더라도 사용자에게 확인을 요청하지 않는다는 기존 제약을 유지한다.

---

## 파일 구조 개요

| 파일 | 상태 | 설명 |
|---|---|---|
| `scripts/run_price_update.ps1` | 신규 | 매시간 실행, 가격/지표만 갱신, LLM 호출 없음 |
| `scripts/run_hourly.ps1` → `scripts/run_scheduled_analysis.ps1` | 이름변경+수정 | 하루 3회 실행, 예산 $3, UTF-8 로그 |
| `.claude/commands/hourly-analysis.md` → `.claude/commands/scheduled-analysis.md` | 이름변경+수정 | 무인 실행 지시문, "되묻지 않기" 문구 보강 |
| `README.md` | 수정 | 자동화 섹션(5번) 갱신 |
| Windows 작업 스케줄러 | 수정 | 기존 작업 액션 교체 + 신규 작업 등록 |

---

### Task 1: 경량 시간별 갱신 스크립트 생성

**Files:**
- Create: `scripts/run_price_update.ps1`

**Interfaces:**
- Consumes: `scripts/fetch_crypto.py`, `scripts/fetch_stocks_kr.py`, `scripts/fetch_stocks_us.py`,
  `scripts/fetch_macro.py`, `scripts/generate_office.py` (기존 스크립트, 인터페이스 변경 없음)
- Produces: `data/*_YYYY-MM-DD.json` 갱신, `office/index.html` 갱신. Task 4에서 이 스크립트를 작업
  스케줄러 액션으로 등록.

- [ ] **Step 1: `scripts/run_price_update.ps1` 생성**

```powershell
# Windows 작업 스케줄러가 매시간 호출하는 경량 갱신 스크립트.
# LLM을 호출하지 않고 가격/지표 데이터만 새로 받아 office 스냅샷을 갱신한다. 비용 없음.

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $ProjectRoot

$pyScripts = @("fetch_crypto.py", "fetch_stocks_kr.py", "fetch_stocks_us.py", "fetch_macro.py", "generate_office.py")
foreach ($script in $pyScripts) {
    try {
        python "scripts\$script"
        if ($LASTEXITCODE -ne 0) {
            Write-Output "실패: $script (종료 코드 $LASTEXITCODE)"
        }
    } catch {
        Write-Output "실패: $script - $_"
    }
}
```

- [ ] **Step 2: 수동 실행으로 검증**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\ai-investment-office\scripts\run_price_update.ps1"`

Expected: 5개 스크립트가 순서대로 실행되고, `data\crypto_오늘날짜.json` 등 4개 데이터 파일과
`office\index.html`의 수정 시각이 방금 실행 시각으로 갱신된다. 실행 시간은 수십 초 내외여야 한다
(WebSearch가 없으므로).

---

### Task 2: 무인 실행 커맨드 이름 변경 + 되묻지 않기 문구 보강

**Files:**
- Create: `.claude/commands/scheduled-analysis.md`
- Delete: `.claude/commands/hourly-analysis.md`

**Interfaces:**
- Consumes: `.claude/agents/*.md`의 9개 애널리스트 + 3개 리서치 종합 + `chief-strategist`
  (agent-roster-consolidation 계획에서 이미 확정된 이름)
- Produces: `/scheduled-analysis` 슬래시 커맨드. Task 3의 `run_scheduled_analysis.ps1`이 이 커맨드를
  호출.

- [ ] **Step 1: `.claude/commands/hourly-analysis.md`의 현재 내용을 확인**

Run: `Get-Content "C:\Users\user\ai-investment-office\.claude\commands\hourly-analysis.md"`

Expected: agent-roster-consolidation 계획의 Task 8에서 갱신된 9개 애널리스트(`candle`/`proto`/`vibes`/
`chart`/`ledger`/`mood`/`trend`/`vault`/`pulse`) + 리서치 종합(`node`/`anchor`/`compass`) 구조가
보여야 한다. 만약 옛 22명 구조(`chain`/`ape`/`fud` 등)가 남아있다면, agent-roster-consolidation 계획을
먼저 완료해야 한다 — 이 태스크를 중단하고 그 계획부터 진행한다.

- [ ] **Step 2: `.claude/commands/scheduled-analysis.md` 생성**

```markdown
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

3. **리서치팀 (데스크별 독립 진행)**: 세 데스크 모두 독립적이므로 한꺼번에 병렬로 호출해도 됩니다.
   - 크립토 데스크: `candle`/`proto`/`vibes` 결과 → `node`에게 전달해 종합
   - 국내주식 데스크: `chart`/`ledger`/`mood` 결과 → `anchor`에게 전달해 종합
   - 해외주식 데스크: `trend`/`vault`/`pulse` 결과 → `compass`에게 전달해 종합

4. **PM**: 2번의 9개 분석 결과와 3번의 리서치 종합 결과(node/anchor/compass 3개)를 `chief-strategist` 서브에이전트에게 전달해 종합 리포트를 `reports/YYYY-MM-DD.md`로 작성(또는 갱신)하게 합니다.

5. `python scripts\generate_office.py`를 실행해 `office\index.html` 스냅샷도 최신 상태로 갱신합니다.

6. 브라우저는 열지 않습니다. 완료되면 생성/갱신된 리포트 경로와 핵심 요약을 짧게 출력하고 종료하세요.
   중간에 예산 문제로 일부만 완료했다면, 어디까지 완료했는지도 함께 출력하세요.
```

- [ ] **Step 3: `.claude/commands/hourly-analysis.md` 삭제**

Run: `Remove-Item "C:\Users\user\ai-investment-office\.claude\commands\hourly-analysis.md"`

- [ ] **Step 4: 수동 검증**

Claude Code에서 `/scheduled-analysis`가 커맨드 목록에 나타나는지, `/hourly-analysis`는 더 이상
나타나지 않는지 확인한다 (Claude Code를 재시작해야 커맨드 목록이 갱신될 수 있음).

---

### Task 3: 전체분석 실행 스크립트 이름 변경 + 예산/로그 인코딩 수정

**Files:**
- Create: `scripts/run_scheduled_analysis.ps1`
- Delete: `scripts/run_hourly.ps1`

**Interfaces:**
- Consumes: `/scheduled-analysis` 슬래시 커맨드 (Task 2), `C:\Users\user\.local\bin\claude.exe`
- Produces: `logs/scheduled_YYYY-MM-DD_HH-mm.log` (UTF-8), `reports/YYYY-MM-DD.md` 갱신. Task 4의
  작업 스케줄러 액션으로 등록.

- [ ] **Step 1: `scripts/run_scheduled_analysis.ps1` 생성**

```powershell
# Windows 작업 스케줄러가 하루 3회(09:00/16:00/23:30) 호출하는 전체분석 스크립트.
# claude -p "/scheduled-analysis" 를 프로젝트 폴더에서 헤드리스로 실행하고 결과를 logs/에 UTF-8로 남긴다.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$LogFile = Join-Path $LogsDir "scheduled_$Timestamp.log"

Set-Location $ProjectRoot

$ClaudeExe = "C:\Users\user\.local\bin\claude.exe"

& $ClaudeExe -p "/scheduled-analysis" --permission-mode acceptEdits --max-budget-usd 3 --output-format text 2>&1 | Out-File -FilePath $LogFile -Encoding utf8

Write-Output "완료: $LogFile"
```

기존 `run_hourly.ps1` 대비 변경점: (1) `--max-budget-usd 5` → `3` (스펙에서 정한 회당 상한과 일치),
(2) `/hourly-analysis` → `/scheduled-analysis`, (3) `*> $LogFile` → `2>&1 | Out-File -FilePath
$LogFile -Encoding utf8` (UTF-16으로 깨지던 로그를 UTF-8로 저장), (4) 로그 파일명 접두사
`hourly_` → `scheduled_` (더 이상 시간별이 아니므로).

- [ ] **Step 2: `scripts/run_hourly.ps1` 삭제**

Run: `Remove-Item "C:\Users\user\ai-investment-office\scripts\run_hourly.ps1"`

- [ ] **Step 3: 수동 실행으로 검증**

Run: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\ai-investment-office\scripts\run_scheduled_analysis.ps1"`

Expected:
- `logs\scheduled_오늘날짜_시분.log` 파일이 생성된다.
- 그 로그 파일을 텍스트 에디터로 열었을 때 한글이 깨지지 않고 정상적으로 읽힌다(이전처럼 UTF-16
  추정 깨짐 문자가 아님).
- `reports\오늘날짜.md`가 끝까지 생성된다(중간에 예산이 부족하면 그 시점까지의 결과라도 로그에
  남아야 하며, "계속할까요?" 같은 질문이 로그에 남아있으면 안 된다).

---

### Task 4: Windows 작업 스케줄러 재구성

**Files:** 없음(시스템 설정 변경, PowerShell 명령으로 수행)

**Interfaces:**
- Consumes: Task 1의 `run_price_update.ps1`, Task 3의 `run_scheduled_analysis.ps1`
- Produces: 재구성된 "AI투자오피스-시간별분석" 작업, 신규 "AI투자오피스-전체분석" 작업

- [ ] **Step 1: 기존 "AI투자오피스-시간별분석" 작업의 액션을 경량 스크립트로 교체**

Run:
```powershell
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\ai-investment-office\scripts\run_price_update.ps1"'
Set-ScheduledTask -TaskName "AI투자오피스-시간별분석" -Action $Action
```

Expected: 명령 실행 후 오류 없이 완료. 트리거(매시간)와 시간제한(20분)은 그대로 유지 — 경량
스크립트는 수십 초 내 끝나므로 문제가 되지 않는다.

- [ ] **Step 2: 신규 "AI투자오피스-전체분석" 작업 등록**

Run:
```powershell
$Action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\Users\user\ai-investment-office\scripts\run_scheduled_analysis.ps1"'
$Trigger1 = New-ScheduledTaskTrigger -Daily -At 09:00
$Trigger2 = New-ScheduledTaskTrigger -Daily -At 16:00
$Trigger3 = New-ScheduledTaskTrigger -Daily -At 23:30
$Settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 55) -DisallowStartIfOnBatteries -StopIfGoingOnBatteries
$Principal = New-ScheduledTaskPrincipal -UserId "user" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName "AI투자오피스-전체분석" -Action $Action -Trigger @($Trigger1, $Trigger2, $Trigger3) -Settings $Settings -Principal $Principal
```

Expected: 명령 실행 후 오류 없이 완료.

- [ ] **Step 3: 두 작업 설정 확인**

Run:
```powershell
Get-ScheduledTask -TaskName "AI투자오피스-시간별분석" | Select-Object TaskName, State
(Get-ScheduledTask -TaskName "AI투자오피스-시간별분석").Actions | Format-List
Get-ScheduledTask -TaskName "AI투자오피스-전체분석" | Select-Object TaskName, State
(Get-ScheduledTask -TaskName "AI투자오피스-전체분석").Actions | Format-List
(Get-ScheduledTask -TaskName "AI투자오피스-전체분석").Triggers | Format-List
(Get-ScheduledTask -TaskName "AI투자오피스-전체분석").Settings.ExecutionTimeLimit
```

Expected: "AI투자오피스-시간별분석"의 Action Argument에 `run_price_update.ps1`이, "AI투자오피스-전체분석"의
Action Argument에 `run_scheduled_analysis.ps1`이 포함되어 있어야 한다. "AI투자오피스-전체분석"의
Triggers는 3개(09:00/16:00/23:30)이고, ExecutionTimeLimit은 `PT55M`이어야 한다.

---

### Task 5: README 자동화 섹션 갱신

**Files:**
- Modify: `README.md`

- [ ] **Step 1: "5. 시간별 자동 AI 분석" 섹션을 아래로 교체**

기존 섹션 제목과 본문(예산 $1, `/hourly-analysis`, `logs\hourly_*.log` 등 언급 부분)을 찾아 아래로
교체한다.

```markdown
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
```

- [ ] **Step 2: 수동 검증**

`README.md`에서 `/hourly-analysis`, `hourly_YYYY-MM-DD_HH-mm.log`, `$1 상한` 등 옛 표현이 더 이상
남아있지 않은지 확인한다.

---

### Task 6: 엔드투엔드 수동 검증

**Files:** 없음(검증 전용)

- [ ] **Step 1: 경량 갱신 확인**

`Get-ScheduledTask -TaskName "AI투자오피스-시간별분석" | Start-ScheduledTask`로 수동 트리거한 뒤 1~2분
기다리고, `data/` 아래 파일들과 `office/index.html`의 수정 시각이 갱신되었는지 확인한다.

- [ ] **Step 2: 전체분석 확인**

`Get-ScheduledTask -TaskName "AI투자오피스-전체분석" | Start-ScheduledTask`로 수동 트리거한 뒤, 완료될
때까지 기다린다(최대 55분, 정상적으로는 그보다 훨씬 빨리 끝나야 한다). 완료 후 다음을 확인한다.
- `logs\scheduled_*.log`가 UTF-8로 정상적으로 읽히는지
- `Get-ScheduledTaskInfo -TaskName "AI투자오피스-전체분석"`의 `LastTaskResult`가 `0`(성공)인지 —
  이전처럼 `3221225786`(강제 종료)이 아닌지 확인
- `reports\오늘날짜.md`가 생성/갱신되었는지
