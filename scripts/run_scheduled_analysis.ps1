# Windows 작업 스케줄러가 하루 3회(09:00/16:00/23:30) 호출하는 전체분석 스크립트.
# claude -p "/scheduled-analysis" 를 프로젝트 폴더에서 헤드리스로 실행하고 결과를 logs/에 UTF-8로 남긴다.
# 이 파일 자체는 UTF-8 BOM 으로 저장한다. BOM 이 없으면 PowerShell 5.1 이 .ps1 을 ANSI(cp949)로
# 읽어 아래 한글 문자열이 깨진다.

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

# ponytail: PowerShell 5.1 은 네이티브 프로세스의 stdout/stderr 바이트를 [Console]::OutputEncoding
# 으로 디코드한 뒤 Out-File 로 다시 인코드한다. 이 PC 의 기본값은 cp949 라서 claude.exe 가 내보낸
# UTF-8 한글이 깨지고, 일부 글자는 '?' 로 바뀌어 복구 불가능해진다(실측: 로그 1개에 '?' 210개).
# 참고: $OutputEncoding 은 이 문제와 무관하다(네이티브 명령에 stdin 으로 보낼 때만 쓰임).
# 실측으로 확인했으니 그쪽으로 바꾸지 말 것.
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# ponytail: $ErrorActionPreference=Stop + "2>&1 |" 조합은 네이티브 stderr 한 줄만 나와도
# NativeCommandError 로 스크립트를 죽인다(워크스페이스 신뢰 경고 등). 이 호출 구간만 Continue 로
# 낮춰서 stderr 도 로그에 남게 한다.
$PrevErrorActionPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $ClaudeExe -p "/scheduled-analysis" --permission-mode acceptEdits --max-budget-usd 3 --output-format text 2>&1 | Out-File -FilePath $LogFile -Encoding utf8
$ErrorActionPreference = $PrevErrorActionPreference

Write-Output "완료: $LogFile"
