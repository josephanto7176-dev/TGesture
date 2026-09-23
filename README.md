# TGesture

TGesture is a Windows 11 background utility intended to turn a two-finger rotation on a Precision Touchpad into rotation commands for the foreground application.

## Important platform constraint

Windows does not expose a universal global "rotate the active image" command. Applications implement rotation differently, and many do not expose it at all. A practical utility therefore needs two layers:

1. A global touchpad gesture reader that computes the signed angle between two contacts.
2. An output adapter selected by the foreground application, such as an application command, automation action, or configurable synthetic input.

The input reader must use a native Windows HID/raw-input component. Ordinary browser pointer events and `WM_GESTURE` only work inside the receiving application and cannot provide the requested system-wide behavior.

## Proposed implementation

- `native/`: Windows HID/raw-input reader and tray process.
- `profiles/`: per-application output mappings.
- `docs/`: decisions and hardware compatibility notes.

The first milestone should log touch contacts and computed angle deltas without sending output. After that is verified on the target laptop, add one output adapter for a known image application and keep a kill switch in the tray menu.

Run the diagnostic from PowerShell with `python native/capture_touchpad.py`. Move two fingers on the touchpad and confirm that hexadecimal reports appear. Stop it with `Ctrl+C`; it does not modify input behavior.

## Run automatically at login

From PowerShell in this folder, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install_startup.ps1
```

TGesture will then run in the background after every Windows sign-in without an open terminal. Remove automatic startup with:

```powershell
.\uninstall_startup.ps1
```

Startup errors are written to `tgesture.log` in this folder.

## Current status

This repository contains the design boundary and a safe starter profile. Building the native component requires Visual Studio 2022 Build Tools with the **Desktop development with C++** workload. A .NET SDK is not currently installed in this environment.
