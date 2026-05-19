# Устанавливает Python (через winget, если нужно), пакет «tasker» и
# tkinterdnd2; создаёт ярлык «Планнер.lnk» на рабочем столе.
# Обычно запускается через install.bat (двойной клик).

$ErrorActionPreference = "Stop"

$projectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pyproject  = Join-Path $projectDir "pyproject.toml"
$icon       = Join-Path $projectDir "icon.ico"

if (-not (Test-Path $pyproject)) {
    Write-Host "ОШИБКА: не найден $pyproject" -ForegroundColor Red
    exit 1
}

function Find-Python {
    $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { return $c }
    }
    return $null
}

function Find-Pythonw {
    param($pythonExe)
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    if ($pythonExe) {
        $pyw = Join-Path (Split-Path $pythonExe -Parent) "pythonw.exe"
        if (Test-Path $pyw) { return $pyw }
    }
    return $pythonExe
}

$python = Find-Python
if (-not $python) {
    Write-Host "Python не найден." -ForegroundColor Yellow
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "Устанавливаю Python через winget (подтвердите UAC)..." -ForegroundColor Cyan
        & winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Установка Python через winget не удалась (код $LASTEXITCODE)." -ForegroundColor Red
            exit 1
        }
        $python = Find-Python
        if (-not $python) {
            Write-Host ""
            Write-Host "Python установлен, но ещё не виден в этом окне." -ForegroundColor Yellow
            Write-Host "Закройте это окно и снова запустите install.bat." -ForegroundColor Yellow
            exit 0
        }
    } else {
        Write-Host "winget недоступен. Установите Python вручную:" -ForegroundColor Red
        Write-Host "  https://www.python.org/downloads/"
        Write-Host "  При установке поставьте галочку 'Add Python to PATH'."
        exit 1
    }
}

Write-Host "Python: $python" -ForegroundColor DarkGray

Write-Host "Устанавливаю пакет «tasker» (editable) с поддержкой DnD..." -ForegroundColor Cyan
& $python -m pip install --user --upgrade --editable "$projectDir[dnd]"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Не удалось установить пакет (код $LASTEXITCODE)." -ForegroundColor Red
    Write-Host "Попробую установить без DnD..." -ForegroundColor Yellow
    & $python -m pip install --user --upgrade --editable $projectDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Установка не удалась полностью." -ForegroundColor Red
        exit 1
    }
    Write-Host "Установлено без tkinterdnd2 — drag-and-drop будет недоступен." -ForegroundColor Yellow
}

$pythonw = Find-Pythonw $python

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "Планнер.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath       = $pythonw
$shortcut.Arguments        = "-m tasker"
$shortcut.WorkingDirectory = $projectDir
if (Test-Path $icon) { $shortcut.IconLocation = $icon }
$shortcut.Description = "Простой планнер задач"
$shortcut.Save()

Write-Host ""
Write-Host "Готово!" -ForegroundColor Green
Write-Host "Ярлык создан на рабочем столе: $shortcutPath"
Write-Host "Запускается:                   $pythonw -m tasker"
Write-Host "Рабочая папка:                 $projectDir"
Write-Host ""
