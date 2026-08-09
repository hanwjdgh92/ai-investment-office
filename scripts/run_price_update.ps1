# Windows 작업 스케줄러가 매시간 호출하는 경량 갱신 스크립트.
# LLM을 호출하지 않고 가격/지표 데이터만 새로 받아 office 스냅샷을 갱신한다. 비용 없음.

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

Set-Location $ProjectRoot

# ponytail: 전체분석(run_scheduled_analysis.ps1)이 최대 55분 돌 수 있어, 매시간 도는 이 스크립트와
# 같은 data/*.json·office/index.html을 동시에 쓸 수 있다. 전체분석이 만든 락 파일이 있으면 이번 회차는 건너뛴다.
$LockFile = Join-Path $ProjectRoot "logs\.scheduled_analysis.lock"
if (Test-Path $LockFile) {
    Write-Output "건너뜀: 전체분석 실행 중 (락 파일 존재: $LockFile)"
    exit 0
}

$hasError = $false
$pyScripts = @("fetch_crypto.py", "fetch_stocks_kr.py", "fetch_stocks_us.py", "fetch_macro.py", "generate_office.py")
foreach ($script in $pyScripts) {
    try {
        python "scripts\$script"
        if ($LASTEXITCODE -ne 0) {
            Write-Output "실패: $script (종료 코드 $LASTEXITCODE)"
            $hasError = $true
        }
    } catch {
        Write-Output "실패: $script - $_"
        $hasError = $true
    }
}

if ($hasError) {
    exit 1
}
