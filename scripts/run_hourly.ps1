# Windows 작업 스케줄러가 1시간마다 호출하는 래퍼 스크립트.
# claude -p "/hourly-analysis" 를 프로젝트 폴더에서 헤드리스로 실행하고 결과를 logs/에 남긴다.

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

$LogsDir = Join-Path $ProjectRoot "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm"
$LogFile = Join-Path $LogsDir "hourly_$Timestamp.log"

Set-Location $ProjectRoot

$ClaudeExe = "C:\Users\user\.local\bin\claude.exe"

& $ClaudeExe -p "/hourly-analysis" --permission-mode acceptEdits --max-budget-usd 5 --output-format text *> $LogFile

Write-Output "완료: $LogFile"
