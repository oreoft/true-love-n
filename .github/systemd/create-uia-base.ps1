#Requires -RunAsAdministrator

$TaskName = "UIA-TL-BASE"
$WorkDir = "\\wsl.localhost\Ubuntu\root\true-love-n\true-love-base"
$VenvPath = "C:\Users\admin\.venvs\true-love-base"
$ScriptDir = "C:\Users\admin\uia-scripts"
$RunnerScript = Join-Path $ScriptDir "run-true-love-base.ps1"

# 确保脚本目录存在
if (!(Test-Path $ScriptDir))
{
    New-Item -ItemType Directory -Path $ScriptDir -Force | Out-Null
}

# 创建运行脚本
$ScriptLines = @(
    "`$Host.UI.RawUI.WindowTitle = `"UIA-TL-BASE`""
    "Set-Location `"$WorkDir`""
    "`$env:UV_PROJECT_ENVIRONMENT = `"$VenvPath`""
    "`$env:UV_VENV_PATH = `"$VenvPath`""
    "Write-Host `"Starting true-love-base at `$(Get-Date)`" -ForegroundColor Cyan"
    "Write-Host `"WorkDir: $WorkDir`" -ForegroundColor Gray"
    "Write-Host `"VenvPath: $VenvPath`" -ForegroundColor Gray"
    "Write-Host `"========================================`" -ForegroundColor Gray"
    "git pull && uv sync --locked && uv run -m true_love_base"
)
$ScriptLines | Out-File -FilePath $RunnerScript -Encoding UTF8 -Force

Write-Host "=== Creating Scheduled Task: $TaskName ===" -ForegroundColor Cyan

# 删除已存在的任务
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue)
{
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# 创建任务
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -NoExit -File `"$RunnerScript`""

$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Highest

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0)

$Task = New-ScheduledTask -Action $Action -Principal $Principal -Settings $Settings

Register-ScheduledTask -TaskName $TaskName -InputObject $Task | Out-Null

Write-Host ""
Write-Host "=== Task Created Successfully ===" -ForegroundColor Green
Write-Host "Task Name : $TaskName"
Write-Host "Runner    : $RunnerScript"
Write-Host ""
Write-Host "Commands:" -ForegroundColor Cyan
Write-Host "  Start  : schtasks /run /tn `"$TaskName`""
Write-Host "  Stop   : schtasks /end /tn `"$TaskName`""
Write-Host "  Status : Get-ScheduledTask -TaskName `"$TaskName`""
Write-Host "  Delete : Unregister-ScheduledTask -TaskName `"$TaskName`" -Confirm:`$false"