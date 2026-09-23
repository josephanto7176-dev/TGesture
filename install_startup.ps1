$ErrorActionPreference = "Stop"

$projectPath = $PSScriptRoot
$python = Get-Command python.exe -ErrorAction Stop
$pythonw = Join-Path (Split-Path $python.Source) "pythonw.exe"
if (-not (Test-Path $pythonw)) {
    throw "pythonw.exe was not found next to python.exe."
}

$scriptPath = Join-Path $projectPath "native\capture_touchpad.py"
$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$command = "`"$pythonw`" `"$scriptPath`" --quiet"
New-ItemProperty -Path $runKey -Name "TGesture Touchpad Rotation" -Value $command -PropertyType String -Force | Out-Null
Unregister-ScheduledTask -TaskName "TGesture Touchpad Rotation" -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "Installed TGesture to start automatically when you sign in."
Start-Process -FilePath $pythonw -ArgumentList "`"$scriptPath`" --quiet" -WorkingDirectory $projectPath