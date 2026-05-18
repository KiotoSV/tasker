# Создаёт ярлык "Планнер.lnk" на рабочем столе с иконкой icon.ico.
# Обычно запускается через install.bat (двойной клик).

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$tasker = Join-Path $projectDir "tasker.py"
$icon   = Join-Path $projectDir "icon.ico"

if (-not (Test-Path $tasker)) {
    Write-Host "ОШИБКА: не найден $tasker" -ForegroundColor Red
    exit 1
}

$pythonw = $null
$pwCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if ($pwCmd) { $pythonw = $pwCmd.Source }
if (-not $pythonw) {
    $pCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pCmd) { $pythonw = $pCmd.Source }
}
if (-not $pythonw) {
    Write-Host "ОШИБКА: не найден Python." -ForegroundColor Red
    Write-Host "Скачайте его с https://www.python.org/downloads/ и при установке"
    Write-Host "поставьте галочку 'Add Python to PATH'."
    exit 1
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Планнер.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = $pythonw
$shortcut.Arguments        = '"' + $tasker + '"'
$shortcut.WorkingDirectory = $projectDir
if (Test-Path $icon) { $shortcut.IconLocation = $icon }
$shortcut.Description = "Простой планнер задач"
$shortcut.Save()

Write-Host ""
Write-Host "Готово!" -ForegroundColor Green
Write-Host "Ярлык создан на рабочем столе: $shortcutPath"
Write-Host "Запускается:                   $pythonw `"$tasker`""
Write-Host ""
