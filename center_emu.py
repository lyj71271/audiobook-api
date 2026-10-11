import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

found = []


@ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
def enum_cb(hwnd, _):
    if not user32.IsWindowVisible(hwnd):
        return True
    length = user32.GetWindowTextLengthW(hwnd)
    if length < 3:
        return True
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    t = buf.value
    if 'pixel' in t.lower() or 'emulator' in t.lower():
        found.append((hwnd, t))
    return True


user32.EnumWindows(enum_cb, 0)
if not found:
    print('NO_EMU_WINDOW')
    raise SystemExit(1)

SM_CXSCREEN, SM_CYSCREEN = 0, 1
sw, sh = user32.GetSystemMetrics(SM_CXSCREEN), user32.GetSystemMetrics(SM_CYSCREEN)
for hwnd, title in found:
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    w, h = r.right - r.left, r.bottom - r.top
    if w <= 0 or h <= 0 or w > sw:
        continue
    x, y = max((sw - w) // 2, 0), max((sh - h) // 2, 0)
    user32.MoveWindow(hwnd, x, y, w, h, True)
    print('moved "%s" to %d,%d size %dx%d (screen %dx%d)' % (title, x, y, w, h, sw, sh))
