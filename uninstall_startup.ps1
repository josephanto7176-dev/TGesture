Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "TGesture Touchpad Rotation" -ErrorAction SilentlyContinue
Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq "C:\Python314\pythonw.exe" } | Stop-Process -Force -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "TGesture Touchpad Rotation" -Confirm:$false -ErrorAction SilentlyContinue
Write-Output "Removed TGesture automatic startup."