"""Capture raw Precision Touchpad HID reports and rotate Photos images."""

import ctypes
import ctypes.wintypes as wintypes
import math
import os
import sys
import argparse
import traceback
from datetime import datetime

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HINSTANCE

WM_INPUT = 0x00FF
WM_DESTROY = 0x0002
RIM_TYPEHID = 2
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100
RID_DEVICE_INFO = 0x2000000B
RIDI_PREPARSEDDATA = 0x20000005
HID_USAGE_PAGE_DIGITIZER = 0x0D
HID_USAGE_TOUCH_PAD = 0x05
VK_CONTROL = 0x11
VK_R = 0x52
KEYEVENTF_KEYUP = 0x0002
ROTATION_STEP_DEGREES = 5.0
PINCH_DISTANCE_CHANGE = 0.12
PHOTOS_PROCESSES = {"Microsoft.Photos.exe", "Photos.exe"}
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tgesture.log")


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HCURSOR),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wintypes.ATOM
user32.DefWindowProcW.argtypes = [
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.DefWindowProcW.restype = ctypes.c_ssize_t


class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [
        ("usUsagePage", wintypes.USHORT),
        ("usUsage", wintypes.USHORT),
        ("dwFlags", wintypes.DWORD),
        ("hwndTarget", wintypes.HWND),
    ]


class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [
        ("dwType", wintypes.DWORD),
        ("dwSize", wintypes.DWORD),
        ("hDevice", wintypes.HANDLE),
        ("wParam", wintypes.WPARAM),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_ulonglong),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUTUNION),
    ]


user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.keybd_event.argtypes = [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_ulonglong]
user32.keybd_event.restype = None
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


user32.CreateWindowExW.argtypes = [
    wintypes.DWORD,
    wintypes.LPCWSTR,
    wintypes.LPCWSTR,
    wintypes.DWORD,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_void_p,
]
user32.CreateWindowExW.restype = ctypes.c_void_p


# LRESULT is pointer-sized; ctypes.wintypes does not define it on every Python build.
WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)


def fail(message):
    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat()} {message}: {ctypes.get_last_error()}\n")
    raise ctypes.WinError(ctypes.get_last_error(), message)


def log_message(message):
    with open(LOG_PATH, "a", encoding="utf-8") as log:
        log.write(f"{datetime.now().isoformat()} {message}\n")


def foreground_process_name():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    process = kernel32.OpenProcess(0x1000, False, process_id.value)
    if not process:
        return ""

    try:
        length = wintypes.DWORD(1024)
        path = ctypes.create_unicode_buffer(length.value)
        if not kernel32.QueryFullProcessImageNameW(process, 0, path, ctypes.byref(length)):
            return ""
        return os.path.basename(path.value)
    finally:
        kernel32.CloseHandle(process)


def rotate_photos(clockwise):
    if foreground_process_name() not in PHOTOS_PROCESSES:
        return False

    turns = 1 if clockwise else 3
    inputs = []
    for _ in range(turns):
        inputs.extend([
            INPUT(1, INPUTUNION(ki=KEYBDINPUT(VK_CONTROL, 0, 0, 0, 0))),
            INPUT(1, INPUTUNION(ki=KEYBDINPUT(VK_R, 0, 0, 0, 0))),
            INPUT(1, INPUTUNION(ki=KEYBDINPUT(VK_R, 0, KEYEVENTF_KEYUP, 0, 0))),
            INPUT(1, INPUTUNION(ki=KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, 0))),
        ])

    input_array = (INPUT * len(inputs))(*inputs)
    if user32.SendInput(len(inputs), input_array, ctypes.sizeof(INPUT)) == len(inputs):
        return True

    for _ in range(turns):
        user32.keybd_event(VK_CONTROL, 0, 0, 0)
        user32.keybd_event(VK_R, 0, 0, 0)
        user32.keybd_event(VK_R, 0, KEYEVENTF_KEYUP, 0)
        user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)
    return True


class TwoFingerRotation:
    """Decode the two contact records observed in the supplied reports."""

    def __init__(self):
        self.contacts = {}
        self.updated_contacts = set()
        self.previous_angle = None
        self.initial_distance = None
        self.pinch_active = False

    def update(self, report):
        if len(report) >= 18 and report[:4] == b"\x0e\x00\x00\x00":
            report = report[8:]
        if len(report) < 6:
            return None

        contact_id = report[1]
        x = int.from_bytes(report[2:4], "little")
        y = int.from_bytes(report[4:6], "little")
        if contact_id in {0x01, 0x11}:
            self.contacts.clear()
            self.updated_contacts.clear()
            self.previous_angle = None
            self.initial_distance = None
            self.pinch_active = False
            return None

        self.contacts[contact_id] = (x, y)
        self.updated_contacts.add(contact_id)
        if len(self.contacts) != 2:
            return None
        if self.updated_contacts != set(self.contacts):
            return None
        self.updated_contacts.clear()

        points = list(self.contacts.values())
        dx = points[1][0] - points[0][0]
        dy = points[1][1] - points[0][1]
        distance = math.hypot(dx, dy)
        angle = math.degrees(math.atan2(dy, dx))
        if self.initial_distance is None:
            self.initial_distance = distance
        elif self.initial_distance and abs(distance - self.initial_distance) / self.initial_distance >= PINCH_DISTANCE_CHANGE:
            self.pinch_active = True

        if self.pinch_active:
            self.previous_angle = angle
            return None
        if self.previous_angle is None:
            self.previous_angle = angle
            return 0.0

        delta = (angle - self.previous_angle + 180.0) % 360.0 - 180.0
        self.previous_angle = angle
        return delta


def main(verbose=True):
    log_message(f"started quiet={not verbose}")
    instance = kernel32.GetModuleHandleW(None)
    class_name = "TGestureRawInputCapture"
    rotation = TwoFingerRotation()
    accumulated_degrees = 0.0
    logged_report_shape = False

    @WNDPROC
    def window_proc(hwnd, message, wparam, lparam):
        nonlocal accumulated_degrees, logged_report_shape
        if message == WM_INPUT:
            size = wintypes.UINT(0)
            user32.GetRawInputData(lparam, RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
            buffer = (ctypes.c_ubyte * size.value)()
            result = user32.GetRawInputData(lparam, RID_INPUT, buffer, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
            if result != 0xFFFFFFFF:
                header = RAWINPUTHEADER.from_buffer(buffer)
                payload = bytes(buffer[ctypes.sizeof(RAWINPUTHEADER):size.value])
                timestamp = datetime.now().isoformat(timespec="milliseconds")
                delta = rotation.update(payload)
                if not verbose:
                    if not logged_report_shape:
                        log_message(f"raw-input bytes={len(payload)} payload={payload.hex()}")
                        logged_report_shape = True
                action = ""
                if delta is not None:
                    accumulated_degrees += delta
                    if abs(accumulated_degrees) >= ROTATION_STEP_DEGREES:
                        clockwise = accumulated_degrees > 0
                        sent = rotate_photos(clockwise)
                        direction = "clockwise" if clockwise else "counterclockwise"
                        action = f" action=photos-rotate-{direction}" if sent else " action=photos-send-failed"
                        accumulated_degrees = 0.0
                        if not verbose:
                            log_message(f"{action.strip()} foreground={foreground_process_name() or 'unknown'}")
                gesture = "" if delta is None else f" rotation_delta={delta:+.2f}deg accumulated={accumulated_degrees:+.2f}deg{action}"
                if verbose:
                    print(f"{timestamp} device=0x{header.hDevice:x} bytes={payload.hex()}{gesture}", flush=True)
                elif action:
                    print(f"{timestamp}{action}", flush=True)
            return 0
        elif message == WM_DESTROY:
            user32.PostQuitMessage(0)
        return user32.DefWindowProcW(hwnd, message, wparam, lparam)

    window_class = WNDCLASSW()
    window_class.lpfnWndProc = ctypes.cast(window_proc, ctypes.c_void_p)
    window_class.hInstance = instance
    window_class.lpszClassName = class_name
    if not user32.RegisterClassW(ctypes.byref(window_class)):
        fail("RegisterClassW failed")

    hwnd = user32.CreateWindowExW(0, class_name, "TGesture raw input", 0, 0, 0, 0, 0, 0, 0, instance, None)
    if not hwnd:
        fail("CreateWindowExW failed")

    device = RAWINPUTDEVICE(HID_USAGE_PAGE_DIGITIZER, HID_USAGE_TOUCH_PAD, RIDEV_INPUTSINK, hwnd)
    if not user32.RegisterRawInputDevices(ctypes.byref(device), 1, ctypes.sizeof(device)):
        fail("RegisterRawInputDevices failed")

    if verbose:
        print("Listening for Precision Touchpad reports. Move two fingers, then press Ctrl+C.")
    message = wintypes.MSG()
    try:
        while user32.GetMessageW(ctypes.byref(message), 0, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
    except KeyboardInterrupt:
        user32.DestroyWindow(hwnd)
        return 0
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true", help="run silently for automatic startup")
    args = parser.parse_args()
    try:
        sys.exit(main(verbose=not args.quiet))
    except Exception:
        log_message(traceback.format_exc())
        raise