<#
.SYNOPSIS
    교육의봄 보도자료 스킬을 Claude Code 사용자 스킬 폴더에 설치합니다.

.DESCRIPTION
    skills/ 아래 두 스킬을 ~/.claude/skills/ 로 복사합니다.
    보도자료 스킬은 hwpx 스킬에 의존하므로 두 개를 함께 설치합니다.

    이미 같은 이름의 스킬이 있으면 덮어쓰기 전에 백업을 만듭니다.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\install.ps1 -WhatIf
    무엇이 설치될지만 보여주고 아무것도 바꾸지 않습니다.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ClaudeHome = (Join-Path $HOME ".claude")
)

$ErrorActionPreference = "Stop"

$source = Join-Path $PSScriptRoot "skills"
$target = Join-Path $ClaudeHome "skills"
$backupRoot = Join-Path $ClaudeHome "backups"

if (-not (Test-Path $source)) {
    throw "skills 폴더를 찾을 수 없습니다: $source`nZIP 압축을 모두 풀었는지 확인하세요."
}

Write-Host ""
Write-Host "교육의봄 보도자료 스킬 설치" -ForegroundColor Cyan
Write-Host "  원본: $source"
Write-Host "  대상: $target"
Write-Host ""

# Claude Code 확인 -- 이게 없으면 스킬을 복사해도 아무 일도 일어나지 않습니다.
# CLI는 PATH에 claude 가 있고, 데스크톱 앱만 쓰는 경우에는 없을 수 있으므로
# ~/.claude 폴더 존재도 함께 봅니다. 둘 다 없으면 미설치로 판단합니다.
$hasClaudeCmd = [bool](Get-Command claude -ErrorAction SilentlyContinue)
$hasClaudeDir = Test-Path $ClaudeHome
if ($hasClaudeCmd -or $hasClaudeDir) {
    Write-Host "  Claude Code: 확인" -ForegroundColor Green
}
else {
    Write-Host "  Claude Code 를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "    이 스킬은 Claude Code 안에서 동작합니다. 먼저 설치하세요:" -ForegroundColor Red
    Write-Host "    https://claude.com/claude-code" -ForegroundColor Red
    Write-Host ""
    Write-Host "  설치를 계속하면 파일은 복사되지만 Claude Code 를 깔기 전까지" -ForegroundColor Yellow
    Write-Host "  아무 일도 일어나지 않습니다." -ForegroundColor Yellow
    Write-Host ""
}

# python 확인 -- 스킬의 생성기가 파이썬으로 동작합니다(표준 라이브러리만 사용).
$pyVersion = $null
try {
    $pyVersion = (& python --version 2>&1) -join ""
    if ($pyVersion -notmatch "Python \d") { $pyVersion = $null; throw "not python" }
    Write-Host "  Python: $pyVersion" -ForegroundColor Green
}
catch {
    $pyVersion = $null
    Write-Host "  Python 을 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "    HWPX 생성이 동작하지 않습니다. 아래 중 하나로 설치하세요:" -ForegroundColor Red
    Write-Host "      winget install --id Python.Python.3.12" -ForegroundColor Red
    Write-Host "      또는 https://www.python.org/downloads/ (설치 시" -ForegroundColor Red
    Write-Host "      'Add python.exe to PATH' 체크 필수)" -ForegroundColor Red
}
Write-Host ""

if (-not (Test-Path $target)) {
    if ($PSCmdlet.ShouldProcess($target, "폴더 생성")) {
        New-Item -ItemType Directory -Force -Path $target | Out-Null
    }
}

$installed = @()
foreach ($dir in Get-ChildItem $source -Directory) {
    $dest = Join-Path $target $dir.Name

    if (Test-Path $dest) {
        $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backup = Join-Path $backupRoot "$($dir.Name)-$stamp.zip"
        Write-Host "  기존 스킬 발견: $($dir.Name)" -ForegroundColor Yellow
        if ($PSCmdlet.ShouldProcess($dest, "백업 후 덮어쓰기")) {
            New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
            Compress-Archive -Path $dest -DestinationPath $backup -Force
            Write-Host "    백업 -> $backup" -ForegroundColor DarkGray
            Remove-Item -Recurse -Force $dest
        }
    }

    if ($PSCmdlet.ShouldProcess($dest, "설치")) {
        Copy-Item -Recurse $dir.FullName $dest
        Get-ChildItem -Recurse $dest -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
        $count = (Get-ChildItem -Recurse $dest -File).Count
        Write-Host "  설치 완료: $($dir.Name)  ($count files)" -ForegroundColor Green
        $installed += $dir.Name
    }
}

if (-not $installed) {
    Write-Host ""
    Write-Host "변경 사항 없음 (-WhatIf 였거나 취소되었습니다)." -ForegroundColor DarkGray
    exit 0
}

# 설치 검증 -- 생성기를 실제로 돌려 봅니다.
Write-Host ""
Write-Host "설치 검증" -ForegroundColor Cyan
$skill = Join-Path $target "spring_press_contents_maker_1.0"
$plan = Join-Path $skill "examples\plan-type-a.json"
$probe = Join-Path $env:TEMP "spring-press-install-check.hwpx"

if ((Test-Path $plan) -and $pyVersion) {
    & python (Join-Path $skill "tools\build_press_release.py") --plan $plan --output $probe 2>&1 |
        Out-Null
    if (Test-Path $probe) {
        & python (Join-Path $skill "tools\verify.py") $probe | Select-Object -Last 1
        Remove-Item $probe -Force -ErrorAction SilentlyContinue
    }
    else {
        Write-Host "  생성 테스트 실패 - 위 오류를 확인하세요." -ForegroundColor Red
    }
}
else {
    Write-Host "  건너뜀 (python 없음)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "완료. Claude Code 를 재시작하면 스킬이 로드됩니다." -ForegroundColor Cyan
Write-Host "  재시작 후: 보도자료를 요청하면 스킬이 자동으로 붙습니다."
Write-Host ""
