import json
import time
import sys
import re
import subprocess
import ctypes
from pathlib import Path

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"

try:
    import tkinter as tk
except ImportError:
    tk = None

if IS_WIN:
    import ctypes.wintypes as wintypes

    HWND_BOTTOM = 1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    SWP_SHOWWINDOW = 0x0040
    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000
    WS_EX_TOOLWINDOW = 0x00000080
    TH32CS_SNAPPROCESS = 0x00000002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260),
        ]

    class MONITORINFOEX(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
            ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD),
            ("szDevice", ctypes.c_wchar * 32),
        ]
else:
    user32 = kernel32 = None

if IS_WIN:
    UI_FONT, MONO_FONT = "Segoe UI", "Consolas"
elif IS_MAC:
    UI_FONT, MONO_FONT = "Helvetica Neue", "Menlo"
else:
    UI_FONT, MONO_FONT = "Sans", "Monospace"

TERMINAL_EXES = {"cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe",
                 "wezterm-gui.exe", "alacritty.exe", "conhost.exe"}
TERMINAL_EXES_UNIX = {"gnome-terminal", "gnome-terminal-server", "konsole", "kitty",
                      "alacritty", "xterm", "tilix", "terminator", "wezterm-gui",
                      "foot", "st", "urxvt", "tmux", "screen", "iterm2", "terminal"}

APP_ALIASES = {
    "chrome": "chrome.exe", "chromium": "chrome.exe", "google chrome": "chrome.exe",
    "google-chrome": "chrome.exe", "microsoft edge": "msedge.exe", "edge": "msedge.exe",
    "firefox": "firefox.exe", "code": "code.exe", "visual studio code": "code.exe",
    "code - oss": "code.exe", "vscodium": "code.exe",
    "iterm2": "windowsterminal.exe", "terminal": "windowsterminal.exe",
    "kitty": "windowsterminal.exe", "gnome-terminal": "windowsterminal.exe",
    "gnome-terminal-server": "windowsterminal.exe", "konsole": "windowsterminal.exe",
    "alacritty": "alacritty.exe", "wezterm": "wezterm-gui.exe",
    "finder": "explorer.exe", "nautilus": "explorer.exe", "files": "explorer.exe",
    "textedit": "notepad.exe", "gedit": "notepad.exe",
    "slack": "slack.exe", "discord": "discord.exe", "spotify": "spotify.exe",
}

_proc_map_cache = {}
_proc_map_ts = 0.0
_monitors_cache = []
_monitors_ts = 0.0


def split_key(key):
    """'Ctrl+X → N' -> [['Ctrl','X'],['N']]; 'Ctrl+C' -> [['Ctrl','C']]."""
    groups = key.split(" → ") if " → " in key else [key]
    return [[k.strip() for k in g.split("+")] if "+" in g else [g.strip()] for g in groups]


class Rect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


def clamp_position(x, y, w, h, rect):
    return (max(rect.left, min(x, rect.right - w)),
            max(rect.top, min(y, rect.bottom - h)))

# ──────────────────── Temas ────────────────────
THEMES = {
    "dark": {
        "bg": "#0a0a0f", "bg_card": "#12121a", "bg_header": "#0f0f18",
        "border": "#1e1e2e", "accent": "#6c5ce7", "accent_dim": "#4a3db8",
        "text": "#e8e8f0", "text_dim": "#6b6b80",
        "key_bg": "#1a1a28", "key_border": "#2a2a3e", "key_text": "#a78bfa",
        "key_highlight": "#222236",
    },
    "light": {
        "bg": "#f5f5f7", "bg_card": "#ffffff", "bg_header": "#eaeaef",
        "border": "#d1d1d6", "accent": "#5856d6", "accent_dim": "#4240b0",
        "text": "#1d1d1f", "text_dim": "#86868b",
        "key_bg": "#e8e8ed", "key_border": "#c7c7cc", "key_text": "#5856d6",
        "key_highlight": "#f0f0f5",
    },
    "cafe": {
        "bg": "#1a1410", "bg_card": "#261c14", "bg_header": "#1f1610",
        "border": "#3e2e1e", "accent": "#d4915e", "accent_dim": "#b07040",
        "text": "#f0e6d8", "text_dim": "#9a8870",
        "key_bg": "#2e2218", "key_border": "#4a3828", "key_text": "#d4915e",
        "key_highlight": "#3a2c1e",
    },
    "natureza": {
        "bg": "#0c1a0f", "bg_card": "#142218", "bg_header": "#0f1c12",
        "border": "#1e3828", "accent": "#4ecb71", "accent_dim": "#38a055",
        "text": "#e0f0e4", "text_dim": "#7a9a80",
        "key_bg": "#1a2e20", "key_border": "#2a4832", "key_text": "#4ecb71",
        "key_highlight": "#203828",
    },
    "ocean": {
        "bg": "#0a0f18", "bg_card": "#101828", "bg_header": "#0c1220",
        "border": "#1c2a40", "accent": "#38bdf8", "accent_dim": "#2898cc",
        "text": "#e0f0ff", "text_dim": "#7090b0",
        "key_bg": "#142030", "key_border": "#243450", "key_text": "#38bdf8",
        "key_highlight": "#1a2840",
    },
    "sunset": {
        "bg": "#180c14", "bg_card": "#241418", "bg_header": "#1c1014",
        "border": "#3a1e2a", "accent": "#f472b6", "accent_dim": "#cc5090",
        "text": "#fce0f0", "text_dim": "#a07088",
        "key_bg": "#2e1820", "key_border": "#482838", "key_text": "#f472b6",
        "key_highlight": "#382030",
    },
}

SETTINGS_FILE = Path(__file__).parent / "settings.json"

def load_settings():
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"theme": "dark", "opacity": 0.95, "display": "fullscreen",
            "always_on_top": False, "font_scale": 1.0}

def save_settings(s):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# ──────────────────── Platform: processes ────────────────────
def _snapshot_processes_win():
    m = {}
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == wintypes.HANDLE(-1).value:
        return m
    try:
        e = PROCESSENTRY32()
        e.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if kernel32.Process32First(snap, ctypes.byref(e)):
            while True:
                name = e.szExeFile.decode("utf-8", errors="ignore").lower()
                m[e.th32ProcessID] = (name, e.th32ParentProcessID)
                if not kernel32.Process32Next(snap, ctypes.byref(e)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    return m


def _snapshot_processes_linux():
    m = {}
    try:
        pids = [p for p in Path("/proc").iterdir() if p.name.isdigit()]
    except OSError:
        return m
    for p in pids:
        try:
            data = (p / "stat").read_text()
            name = data[data.index("(") + 1:data.rindex(")")]
            rest = data[data.rindex(")") + 2:].split()
            m[int(p.name)] = (name.lower(), int(rest[1]))
        except (OSError, ValueError, IndexError):
            continue
    return m


def _snapshot_processes_mac():
    m = {}
    try:
        out = subprocess.run(["ps", "-axo", "pid=,ppid=,comm="],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return m
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3:
            try:
                m[int(parts[0])] = (Path(parts[2]).name.lower(), int(parts[1]))
            except ValueError:
                continue
    return m


def _get_process_map():
    """Snapshot pid -> (name, ppid), cached 2s."""
    global _proc_map_ts
    now = time.time()
    if _proc_map_cache and now - _proc_map_ts < 2:
        return _proc_map_cache
    if IS_WIN:
        m = _snapshot_processes_win()
    elif IS_MAC:
        m = _snapshot_processes_mac()
    else:
        m = _snapshot_processes_linux()
    _proc_map_cache.clear()
    _proc_map_cache.update(m)
    _proc_map_ts = now
    return _proc_map_cache


def _has_opencode_descendant(root_pid):
    """True if any opencode process lives BELOW root_pid in the tree.

    opencode runs as: terminal -> shell -> (shim) -> opencode,
    so we walk UP from each opencode process looking for root_pid.
    """
    pmap = _get_process_map()
    for pid in pmap:
        if "opencode" not in pmap[pid][0]:
            continue
        cur, depth = pid, 0
        while cur in pmap and depth < 15:
            if cur == root_pid:
                return True
            cur = pmap[cur][1]
            depth += 1
    return False


# ──────────────────── Platform: foreground app ────────────────────
def get_exe_path(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    handle = kernel32.OpenProcess(0x1000, False, pid.value)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wintypes.DWORD(512)
        kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size))
        return Path(buf.value).name.lower()
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(handle)


def _foreground_win():
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return ""
    exe = get_exe_path(hwnd)
    if exe.startswith("opencode"):
        return "opencode.exe"
    if exe in TERMINAL_EXES:
        title_buf = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title_buf, 256)
        if "opencode" in title_buf.value.lower():
            return "opencode.exe"
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        root = pid.value
        if exe == "conhost.exe":
            pmap = _get_process_map()
            if root in pmap:
                root = pmap[root][1]
        if _has_opencode_descendant(root):
            return "opencode.exe"
    return exe


def _foreground_linux():
    try:
        out = subprocess.run(["xprop", "-root", "_NET_ACTIVE_WINDOW"],
                             capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return ""
    m = re.search(r"window id # (0x[0-9a-fA-F]+)", out)
    if not m:
        return ""
    wid = m.group(1)
    try:
        info = subprocess.run(["xprop", "-id", wid, "_NET_WM_PID", "WM_CLASS"],
                              capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return ""
    pid_m = re.search(r"_NET_WM_PID\(CARDINAL\) = (\d+)", info)
    exe = ""
    if pid_m:
        try:
            exe = Path(f"/proc/{pid_m.group(1)}/comm").read_text().strip().lower()
        except OSError:
            pass
    if not exe:
        cls = re.search(r'WM_CLASS\(STRING\) = "[^"]*", "([^"]+)"', info)
        if cls:
            exe = cls.group(1).lower()
    if not exe:
        return ""
    if exe in TERMINAL_EXES_UNIX and pid_m and _has_opencode_descendant(int(pid_m.group(1))):
        return "opencode.exe"
    if "opencode" in exe:
        return "opencode.exe"
    return exe


def _foreground_mac():
    try:
        out = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get {unix id, name} of '
             'first application process whose frontmost is true'],
            capture_output=True, text=True, timeout=3).stdout.strip()
    except Exception:
        return ""
    parts = out.split(", ", 1)
    if len(parts) != 2 or not parts[0].isdigit():
        return ""
    pid, name = int(parts[0]), parts[1].strip().lower()
    proc = _get_process_map().get(pid, ("", 0))[0]
    if (proc in TERMINAL_EXES_UNIX or name in TERMINAL_EXES_UNIX) and _has_opencode_descendant(pid):
        return "opencode.exe"
    if "opencode" in proc or "opencode" in name:
        return "opencode.exe"
    return name


def get_foreground_exe():
    if IS_WIN:
        return _foreground_win()
    if IS_MAC:
        return _foreground_mac()
    return _foreground_linux()


# ──────────────────── Platform: monitors ────────────────────
def _monitors_win():
    monitors = []
    def cb(hmon, hdc, lprect, lparam):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            monitors.append({
                "left": mi.rcMonitor.left, "top": mi.rcMonitor.top,
                "width": mi.rcMonitor.right - mi.rcMonitor.left,
                "height": mi.rcMonitor.bottom - mi.rcMonitor.top,
            })
        return 1
    ENUMPROC = ctypes.WINFUNCTYPE(
        wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
        ctypes.POINTER(wintypes.RECT), wintypes.LPARAM
    )
    user32.EnumDisplayMonitors(None, None, ENUMPROC(cb), 0)
    return monitors


def _monitors_linux():
    try:
        out = subprocess.run(["xrandr", "--query"],
                             capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return []
    found = []
    for line in out.splitlines():
        m = re.match(r"^(\S+) connected (primary )?(\d+)x(\d+)\+(\d+)\+(\d+)", line)
        if m:
            w, h, x, y = map(int, m.group(3, 4, 5, 6))
            found.append((m.group(2) is not None,
                          {"left": x, "top": y, "width": w, "height": h}))
    found.sort(key=lambda t: not t[0])
    return [d for _, d in found]


def _monitors_mac():
    try:
        cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")

        class CGPoint(ctypes.Structure):
            _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]

        class CGSize(ctypes.Structure):
            _fields_ = [("w", ctypes.c_double), ("h", ctypes.c_double)]

        class CGRect(ctypes.Structure):
            _fields_ = [("origin", CGPoint), ("size", CGSize)]

        cg.CGDisplayBounds.restype = CGRect
        ids = (ctypes.c_uint32 * 16)()
        n = ctypes.c_uint32()
        if cg.CGGetActiveDisplayList(16, ids, ctypes.byref(n)) != 0 or n.value == 0:
            return []
        return [{"left": int(r.origin.x), "top": int(r.origin.y),
                 "width": int(r.size.w), "height": int(r.size.h)}
                for r in (cg.CGDisplayBounds(ids[i]) for i in range(n.value))]
    except Exception:
        return []


def _monitors_tk():
    if tk is None:
        return []
    try:
        r = tk.Tk()
        r.withdraw()
        w, h = r.winfo_screenwidth(), r.winfo_screenheight()
        r.destroy()
        return [{"left": 0, "top": 0, "width": w, "height": h}]
    except Exception:
        return []


def get_all_monitors():
    global _monitors_ts
    now = time.time()
    if _monitors_cache and now - _monitors_ts < 5:
        return _monitors_cache
    if IS_WIN:
        mons = _monitors_win()
    elif IS_MAC:
        mons = _monitors_mac() or _monitors_tk()
    else:
        mons = _monitors_linux() or _monitors_tk()
    _monitors_cache[:] = mons
    _monitors_ts = now
    return _monitors_cache


def get_second_monitor():
    if IS_WIN:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
    mons = get_all_monitors()
    if len(mons) >= 2:
        return mons[1]
    return mons[0] if mons else None


def get_monitor_work_rect(x, y):
    if IS_WIN:
        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]
        user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
        user32.MonitorFromPoint.restype = wintypes.HMONITOR
        hmon = user32.MonitorFromPoint(POINT(x, y), 2)
        if not hmon:
            return None
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(MONITORINFOEX)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            return mi.rcWork
        return None
    for mon in get_all_monitors():
        if (mon["left"] <= x < mon["left"] + mon["width"]
                and mon["top"] <= y < mon["top"] + mon["height"]):
            top = mon["top"] + (30 if IS_MAC else 0)
            return Rect(mon["left"], top,
                        mon["left"] + mon["width"], mon["top"] + mon["height"])
    return None


# ──────────────────── Tooltip ────────────────────
class Tooltip:
    def __init__(self, widget, get_key, get_info, get_colors):
        self.widget = widget
        self.get_key = get_key
        self.get_info = get_info
        self.get_colors = get_colors
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _e=None):
        if self.tip:
            return
        c = self.get_colors()
        x, y = self.widget.winfo_pointerxy()
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_attributes("-topmost", True)

        outer = tk.Frame(self.tip, bg=c["border"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        frame = tk.Frame(outer, bg=c["key_bg"], padx=12, pady=9)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text=self.get_key(), font=(MONO_FONT, 10, "bold"),
                 bg=c["key_bg"], fg=c["key_text"], anchor="w").pack(fill="x")
        tk.Label(frame, text=self.get_info(), font=(UI_FONT, 10),
                 bg=c["key_bg"], fg=c["text"], wraplength=340,
                 justify="left", anchor="w").pack(fill="x", pady=(5, 0))

        self.tip.update_idletasks()
        tw, th = self.tip.winfo_reqwidth(), self.tip.winfo_reqheight()
        tx, ty = x + 14, y + 14
        rect = get_monitor_work_rect(x, y)
        if rect:
            if tx + tw > rect.right:
                tx = x - tw - 14
            if ty + th > rect.bottom:
                ty = y - th - 14
            tx = max(tx, rect.left + 4)
            ty = max(ty, rect.top + 4)
        self.tip.wm_geometry(f"+{tx}+{ty}")

    def _hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


# ──────────────────── Settings Window ────────────────────
class SettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self._orig = dict(parent.settings)
        self.win = tk.Toplevel(parent.root)
        self.win.title("Configurações")
        self.win.geometry("480x560")
        self.win.configure(bg=parent.c["bg"])
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)

        px = parent.root.winfo_x() + parent.root.winfo_width() // 2 - 240
        py = parent.root.winfo_y() + parent.root.winfo_height() // 2 - 280
        self.win.geometry(f"+{px}+{py}")

        self.tabs = {}
        self.pages = {}
        self._build()

    def _build(self):
        c = self.parent.c

        tk.Label(self.win, text="CONFIGURAÇÕES", font=(MONO_FONT, 12, "bold"),
                 bg=c["bg_header"], fg=c["accent"]).pack(fill="x", ipady=8)
        tk.Frame(self.win, bg=c["accent"], height=2).pack(fill="x")

        # Tab bar
        tabbar = tk.Frame(self.win, bg=c["bg_header"])
        tabbar.pack(fill="x")
        for name in ("Aparência", "Janela"):
            b = tk.Label(tabbar, text=f"  {name}  ", font=(UI_FONT, 10, "bold"),
                         bg=c["bg_header"], fg=c["text_dim"], cursor="hand2")
            b.pack(side="left", padx=(12, 0), pady=(6, 0), ipadx=6, ipady=5)
            b.bind("<Button-1>", lambda e, n=name: self._switch(n))
            self.tabs[name] = b

        self.pages["Aparência"] = tk.Frame(self.win, bg=c["bg"], padx=22, pady=15)
        self.pages["Janela"] = tk.Frame(self.win, bg=c["bg"], padx=22, pady=15)
        self._build_aparencia(self.pages["Aparência"])
        self._build_janela(self.pages["Janela"])

        # Buttons (bottom, shared)
        btn_frame = tk.Frame(self.win, bg=c["bg"], padx=22, pady=12)
        btn_frame.pack(fill="x", side="bottom")
        tk.Button(btn_frame, text="Aplicar", font=(UI_FONT, 10, "bold"),
                  bg=c["accent"], fg="#ffffff", relief="flat", padx=20, pady=6,
                  command=self._apply).pack(side="right", padx=(8, 0))
        tk.Button(btn_frame, text="Cancelar", font=(UI_FONT, 10),
                  bg=c["key_bg"], fg=c["text"], relief="flat", padx=20, pady=6,
                  command=self._cancel).pack(side="right")

        self._switch("Aparência")

    def _switch(self, name):
        c = self.parent.c
        for n, page in self.pages.items():
            if n == name:
                page.pack(fill="both", expand=True)
                self.tabs[n].config(bg=c["bg"], fg=c["accent"])
            else:
                page.pack_forget()
                self.tabs[n].config(bg=c["bg_header"], fg=c["text_dim"])

    def _section(self, parent, title, subtitle):
        c = self.parent.c
        tk.Label(parent, text=title, font=(UI_FONT, 11, "bold"),
                 bg=c["bg"], fg=c["text"]).pack(anchor="w")
        if subtitle:
            tk.Label(parent, text=subtitle, font=(UI_FONT, 9),
                     bg=c["bg"], fg=c["text_dim"]).pack(anchor="w", pady=(0, 6))

    def _build_aparencia(self, body):
        c = self.parent.c

        # Tema
        self._section(body, "Tema", "Escolha entre tema claro ou escuro")
        theme_frame = tk.Frame(body, bg=c["bg"])
        theme_frame.pack(fill="x", pady=(0, 15))
        self.theme_var = tk.StringVar(value=self.parent.settings["theme"])
        for key, label in [("dark", "Escuro"), ("light", "Claro")]:
            tk.Radiobutton(theme_frame, text=label, variable=self.theme_var, value=key,
                           font=(UI_FONT, 10), bg=c["bg"], fg=c["text"],
                           selectcolor=c["key_bg"], activebackground=c["bg"],
                           activeforeground=c["text"], command=self._preview_theme
                           ).pack(side="left", padx=(0, 20))

        # Esquema de Cores
        self._section(body, "Esquema de Cores", "Paleta aplicada ao tema")
        scheme_frame = tk.Frame(body, bg=c["bg"])
        scheme_frame.pack(fill="x", pady=(0, 15))
        self.scheme_var = tk.StringVar(value=self.parent.settings.get("scheme", "dark"))
        for key, label, color in [
            ("dark", "Padrão", "#6c5ce7"), ("cafe", "Café", "#d4915e"),
            ("natureza", "Natureza", "#4ecb71"), ("ocean", "Oceano", "#38bdf8"),
            ("sunset", "Pôr do Sol", "#f472b6"),
        ]:
            row = tk.Frame(scheme_frame, bg=c["bg"])
            row.pack(fill="x", pady=2)
            tk.Label(row, text="●", font=(UI_FONT, 14), bg=c["bg"],
                     fg=color, width=2).pack(side="left")
            tk.Radiobutton(row, text=label, variable=self.scheme_var, value=key,
                           font=(UI_FONT, 10), bg=c["bg"], fg=c["text"],
                           selectcolor=c["key_bg"], activebackground=c["bg"],
                           activeforeground=c["text"], indicatoron=False, padx=8, pady=2,
                           command=self._preview_theme).pack(side="left", fill="x", expand=True)

        # Opacidade
        self._section(body, "Opacidade do Fundo", None)
        self.opacity_var = tk.DoubleVar(value=self.parent.settings.get("opacity", 0.95))
        self.opacity_label = tk.Label(body, text=f"{int(self.opacity_var.get()*100)}%",
                                      font=(UI_FONT, 10), bg=c["bg"], fg=c["text_dim"])
        self.opacity_label.pack(anchor="e")
        tk.Scale(body, from_=0.3, to=1.0, resolution=0.05, orient="horizontal",
                 variable=self.opacity_var, bg=c["bg"], fg=c["text"],
                 troughcolor=c["key_bg"], highlightthickness=0, length=400,
                 command=lambda v: self.opacity_label.config(text=f"{int(float(v)*100)}%")
                 ).pack(fill="x", pady=(0, 15))

        # Tamanho da Fonte
        self._section(body, "Tamanho da Fonte", "Escala aplicada a textos e teclas")
        self.fontscale_var = tk.DoubleVar(value=self.parent.settings.get("font_scale", 1.0))
        self.fontscale_label = tk.Label(body, text=f"{int(self.fontscale_var.get()*100)}%",
                                        font=(UI_FONT, 10), bg=c["bg"], fg=c["text_dim"])
        self.fontscale_label.pack(anchor="e")
        fs_scale = tk.Scale(body, from_=0.8, to=1.6, resolution=0.05, orient="horizontal",
                            variable=self.fontscale_var, bg=c["bg"], fg=c["text"],
                            troughcolor=c["key_bg"], highlightthickness=0, length=400,
                            command=lambda v: self.fontscale_label.config(text=f"{int(float(v)*100)}%"))
        fs_scale.pack(fill="x")
        fs_scale.bind("<ButtonRelease-1>", self._preview_font)

    def _build_janela(self, body):
        c = self.parent.c

        # Modo de Exibição
        self._section(body, "Modo de Exibição", "Tela cheia (segundo monitor) ou widget compacto")
        self.display_var = tk.StringVar(value=self.parent.settings.get("display", "fullscreen"))
        for key, label, desc in [
            ("fullscreen", "Tela Cheia", "Preenche o segundo monitor"),
            ("widget", "Widget", "Janela compacta no canto"),
        ]:
            row = tk.Frame(body, bg=c["bg"])
            row.pack(fill="x", pady=2)
            tk.Radiobutton(row, text=label, variable=self.display_var, value=key,
                           font=(UI_FONT, 10), bg=c["bg"], fg=c["text"],
                           selectcolor=c["key_bg"], activebackground=c["bg"],
                           activeforeground=c["text"]).pack(side="left")
            tk.Label(row, text=desc, font=(UI_FONT, 9), bg=c["bg"],
                     fg=c["text_dim"]).pack(side="left", padx=(8, 0))
        tk.Label(body, text="Arraste pela barra do topo para mover; pelo canto ◢ para redimensionar.\nPosição e tamanho são memorizados automaticamente.",
                 font=(UI_FONT, 9), bg=c["bg"], fg=c["text_dim"],
                 justify="left").pack(anchor="w", pady=(4, 0))
        tk.Frame(body, bg=c["bg"]).pack(pady=6)

        # Sempre no Topo
        self._section(body, "Janela", "Comportamento da janela")
        self.topmost_var = tk.BooleanVar(value=self.parent.settings.get("always_on_top", False))
        tk.Checkbutton(body, text="Sempre no topo", variable=self.topmost_var,
                       font=(UI_FONT, 10), bg=c["bg"], fg=c["text"],
                       selectcolor=c["key_bg"], activebackground=c["bg"],
                       activeforeground=c["text"]).pack(anchor="w")
        tk.Label(body, text="A janela fica acima de outras janelas (desativado por padrão)",
                 font=(UI_FONT, 9), bg=c["bg"], fg=c["text_dim"]).pack(anchor="w", padx=(22, 0))

        tk.Button(body, text="Restaurar posição e tamanho padrão", font=(UI_FONT, 10),
                  bg=c["key_bg"], fg=c["text"], relief="flat", padx=12, pady=4,
                  command=self._reset_geometry).pack(anchor="w", pady=(12, 0))

    def _merged_colors(self):
        theme = self.theme_var.get()
        scheme = self.scheme_var.get()
        t = THEMES.get(theme, THEMES["dark"])
        s = THEMES.get(scheme, t)
        merged = {**t}
        for k in ("accent", "accent_dim", "key_text"):
            if k in s:
                merged[k] = s[k]
        return merged

    def _preview_theme(self):
        self.parent.c = self._merged_colors()
        self.parent.root.configure(bg=self.parent.c["bg"])
        self.parent._rebuild_ui()

    def _preview_font(self, _e=None):
        self.parent.settings["font_scale"] = round(self.fontscale_var.get(), 2)
        self.parent._rebuild_ui()

    def _apply(self):
        p = self.parent
        p.settings["theme"] = self.theme_var.get()
        p.settings["scheme"] = self.scheme_var.get()
        p.settings["opacity"] = self.opacity_var.get()
        p.settings["font_scale"] = round(self.fontscale_var.get(), 2)
        p.settings["display"] = self.display_var.get()
        p.settings["always_on_top"] = self.topmost_var.get()
        save_settings(p.settings)

        p.c = self._merged_colors()
        p.root.configure(bg=p.c["bg"])
        p.root.attributes("-alpha", p.settings["opacity"])
        p.root.attributes("-topmost", p.settings["always_on_top"])
        p._rebuild_ui_with_relayout()
        self.win.destroy()

    def _cancel(self):
        p = self.parent
        p.settings.clear()
        p.settings.update(self._orig)
        p.root.attributes("-alpha", p.settings.get("opacity", 0.95))
        p.root.attributes("-topmost", p.settings.get("always_on_top", False))
        p._rebuild_ui_with_relayout()
        self.win.destroy()

    def _reset_geometry(self):
        p = self.parent
        for k in ("widget_x", "widget_y", "widget_w", "widget_h",
                  "win_x", "win_y", "win_w", "win_h"):
            p.settings.pop(k, None)
        save_settings(p.settings)
        p._rebuild_ui_with_relayout()


# ──────────────────── Main ────────────────────
class ShortcutsWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OpenFocusKeys")
        self.root.overrideredirect(True)

        self.settings = load_settings()
        self._load_shortcuts()

        theme = self.settings.get("theme", "dark")
        scheme = self.settings.get("scheme", "dark")
        t = THEMES.get(theme, THEMES["dark"])
        s = THEMES.get(scheme, t)
        self.c = {**t}
        for k in ("accent", "accent_dim", "key_text"):
            if k in s:
                self.c[k] = s[k]

        self.root.configure(bg=self.c["bg"])
        self.root.attributes("-alpha", self.settings.get("opacity", 0.95))

        self._setup_window()
        self._build_ui()
        self._current_app = ""
        self._poll_focus()

    def _fs(self, base):
        """Font size scaled by user setting."""
        return max(7, int(round(base * self.settings.get("font_scale", 1.0))))

    def _load_shortcuts(self):
        data_path = Path(__file__).parent / "shortcuts.json"
        with open(data_path, encoding="utf-8") as f:
            self.shortcut_data = json.load(f)

    def _setup_window(self):
        display = self.settings.get("display", "fullscreen")
        always_top = self.settings.get("always_on_top", False)
        self.root.attributes("-topmost", always_top)

        monitor = get_second_monitor()
        pref = "widget_" if display == "widget" else "win_"
        s = self.settings

        if display == "widget":
            dw, dh = 380, 340
            if monitor:
                dx = monitor["left"] + monitor["width"] - dw - 20
                dy = monitor["top"] + monitor["height"] - dh - 20
            else:
                dx = self.root.winfo_screenwidth() - dw - 20
                dy = self.root.winfo_screenheight() - dh - 60
        else:
            if monitor:
                dx, dy = monitor["left"], monitor["top"]
                dw, dh = monitor["width"], monitor["height"]
            else:
                dw, dh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
                dx, dy = 0, 0

        ww = max(300, int(s.get(pref + "w", dw)))
        wh = max(240, int(s.get(pref + "h", dh)))
        x = int(s.get(pref + "x", dx))
        y = int(s.get(pref + "y", dy))

        if s.get(pref + "x") is not None:
            rect = get_monitor_work_rect(x, y)
            if rect:
                x, y = clamp_position(x, y, ww, wh, rect)

        self.root.geometry(f"{ww}x{wh}+{x}+{y}")

        self.root.update_idletasks()
        self.root.update()
        self._apply_window_hints()
        self.root.bind("<FocusIn>", lambda e: self.root.after(1, self._send_to_back))
        self.root.bind("<Map>", lambda e: self.root.after(50, self._send_to_back))

    def _apply_window_hints(self):
        if IS_WIN:
            hwnd = int(self.root.wm_frame(), 16)
            ex = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW)
            self._send_to_back()
        elif not IS_MAC:
            try:
                subprocess.run(["xprop", "-id", str(self.root.winfo_id()),
                                "-f", "_NET_WM_STATE", "32a", "-set", "_NET_WM_STATE",
                                "_NET_WM_STATE_BELOW,_NET_WM_STATE_SKIP_TASKBAR"],
                               capture_output=True, timeout=2)
            except Exception:
                pass

    def _send_to_back(self):
        if self.settings.get("always_on_top", False) or not IS_WIN:
            return
        hwnd = int(self.root.wm_frame(), 16)
        user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW)

    def _grip_start(self, e):
        self._gx0, self._gy0 = e.x_root, e.y_root
        self._gw0, self._gh0 = self.root.winfo_width(), self.root.winfo_height()

    def _grip_drag(self, e):
        w = max(300, self._gw0 + e.x_root - self._gx0)
        h = max(240, self._gh0 + e.y_root - self._gy0)
        mon = get_second_monitor()
        if mon:
            w, h = min(w, mon["width"]), min(h, mon["height"])
        self.root.geometry(f"{w}x{h}+{self.root.winfo_x()}+{self.root.winfo_y()}")

    def _grip_end(self, _e=None):
        self._save_geometry()
        if self._current_app:
            self._update_shortcuts(self._current_app)

    def _save_geometry(self):
        pref = "widget_" if self.settings.get("display") == "widget" else "win_"
        self.settings[pref + "x"] = self.root.winfo_x()
        self.settings[pref + "y"] = self.root.winfo_y()
        self.settings[pref + "w"] = self.root.winfo_width()
        self.settings[pref + "h"] = self.root.winfo_height()
        save_settings(self.settings)

    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        if not hasattr(self, "_dx"):
            return
        self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")

    def _drag_end(self, _e=None):
        if hasattr(self, "_dx"):
            del self._dx, self._dy
        self._save_geometry()

    def _bind_drag_tree(self, widget):
        skip = (getattr(self, "menu_btn", None), getattr(self, "grip_btn", None))
        if widget not in skip:
            widget.bind("<ButtonPress-1>", self._drag_start)
            widget.bind("<B1-Motion>", self._drag_move)
            widget.bind("<ButtonRelease-1>", self._drag_end)
        for child in widget.winfo_children():
            if not isinstance(child, tk.Toplevel):
                self._bind_drag_tree(child)

    def _apply_colors(self, colors):
        self.c = colors
        self.root.configure(bg=colors["bg"])
        self._rebuild_ui()

    def _rebuild_ui(self):
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self._build_ui()
        if self._current_app:
            self._update_shortcuts(self._current_app)

    def _rebuild_ui_with_relayout(self):
        self._setup_window()
        self._rebuild_ui()

    def _build_ui(self):
        c = self.c
        display = self.settings.get("display", "fullscreen")
        is_widget = display == "widget"

        if is_widget:
            margin, header_h = 12, 50
            title_size, app_size = self._fs(9), self._fs(13)
        else:
            ww = self.root.winfo_width()
            margin = max(20, int(ww * 0.05))
            header_h = 70
            title_size, app_size = self._fs(11), self._fs(18)

        tk.Frame(self.root, bg=c["accent"], height=3).pack(fill="x")

        header = tk.Frame(self.root, bg=c["bg_header"], height=header_h)
        header.pack(fill="x")
        header.pack_propagate(False)

        left = tk.Frame(header, bg=c["bg_header"])
        left.pack(side="left", fill="y", padx=(margin, 0))
        tk.Label(left, text="OPENFOCUSKEYS", font=(MONO_FONT, title_size, "bold"),
                 bg=c["bg_header"], fg=c["accent"]).pack(anchor="w", pady=(10, 0))
        self.app_label = tk.Label(left, text="Aguardando foco...",
                                  font=(UI_FONT, app_size, "bold"),
                                  bg=c["bg_header"], fg=c["text"])
        self.app_label.pack(anchor="w")

        right = tk.Frame(header, bg=c["bg_header"])
        right.pack(side="right", fill="y", padx=(0, margin))
        self.menu_btn = tk.Label(right, text="☰", font=(UI_FONT, 18),
                                 bg=c["bg_header"], fg=c["text_dim"], cursor="hand2")
        self.menu_btn.pack(side="right", padx=(10, 0), pady=10)
        self.menu_btn.bind("<Button-1>", self._show_menu)
        tk.Label(right, text="●", font=(UI_FONT, 12),
                 bg=c["bg_header"], fg="#00b894").pack(side="right", pady=14)

        tk.Frame(self.root, bg=c["border"], height=1).pack(fill="x", padx=margin)
        self.container = tk.Frame(self.root, bg=c["bg"])
        self.container.pack(fill="both", expand=True, padx=margin, pady=6)

        self.grip_btn = tk.Label(self.root, text="◢", font=(UI_FONT, 11, "bold"),
                                 bg=c["bg_header"], fg=c["text_dim"], cursor="size_nw_se",
                                 padx=5, pady=3)
        self.grip_btn.place(relx=1.0, rely=1.0, anchor="se")
        self.grip_btn.bind("<ButtonPress-1>", self._grip_start)
        self.grip_btn.bind("<B1-Motion>", self._grip_drag)
        self.grip_btn.bind("<ButtonRelease-1>", self._grip_end)
        self._bind_drag_tree(self.root)

    def _show_menu(self, _event=None):
        c = self.c
        menu = tk.Menu(self.root, tearoff=0, bg=c["bg_header"], fg=c["text"],
                       activebackground=c["accent"], activeforeground="#ffffff",
                       font=(UI_FONT, 10))
        menu.add_command(label="⚙  Configurações", command=self._open_settings)
        menu.add_separator()
        menu.add_command(label="ℹ  Sobre", command=self._show_about)
        menu.add_separator()
        menu.add_command(label="✕  Fechar", command=self._quit)
        menu.post(self.menu_btn.winfo_rootx(), self.menu_btn.winfo_rooty() + 30)

    def _quit(self):
        self.root.destroy()

    def _open_settings(self):
        SettingsWindow(self)

    def _show_about(self):
        c = self.c
        about = tk.Toplevel(self.root)
        about.title("Sobre")
        about.geometry("360x260")
        about.configure(bg=c["bg"])
        about.resizable(False, False)
        about.attributes("-toolwindow", True)
        about.attributes("-topmost", True)

        px = self.root.winfo_x() + self.root.winfo_width() // 2 - 180
        py = self.root.winfo_y() + self.root.winfo_height() // 2 - 130
        about.geometry(f"+{px}+{py}")

        tk.Frame(about, bg=c["accent"], height=3).pack(fill="x")
        tk.Label(about, text="OPENFOCUSKEYS", font=(MONO_FONT, 14, "bold"),
                 bg=c["bg"], fg=c["accent"]).pack(pady=(25, 5))
        tk.Label(about, text="v1.2", font=(MONO_FONT, 10),
                 bg=c["bg"], fg=c["text_dim"]).pack()
        tk.Label(about, text="\nExibe atalhos de teclado na segunda tela\nconforme o programa em foco.\n\nPasse o mouse no (i) de cada atalho\npara ver a explicação detalhada.",
                 font=(UI_FONT, 10), bg=c["bg"], fg=c["text"],
                 justify="center").pack(pady=(10, 15))
        tk.Button(about, text="OK", font=(UI_FONT, 10, "bold"),
                  bg=c["accent"], fg="#ffffff", relief="flat", padx=30, pady=4,
                  command=about.destroy).pack()

    def _lookup(self, app_name):
        d = self.shortcut_data
        if app_name in d:
            return app_name
        low = app_name.lower()
        alias = APP_ALIASES.get(low)
        if alias and alias in d:
            return alias
        for guess in (low, low + ".exe"):
            if guess in d:
                return guess
        return "_default"

    def _clear_shortcuts(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _make_card(self, parent, item, row, col, display="fullscreen"):
        c = self.c
        is_widget = display == "widget"
        key, desc = item["key"], item["desc"]
        info = item.get("info", desc)

        card = tk.Frame(parent, bg=c["bg_card"])
        card.grid(row=row, column=col, padx=4, pady=3, sticky="nsew")

        key_font = self._fs(10 if is_widget else 11)
        key_row = tk.Frame(card, bg=c["bg_card"])
        key_row.pack(fill="x", padx=8, pady=(6, 3))

        # Info icon (i) — hover for explanation
        self._draw_info_icon(key_row, key, info)

        for j, keys in enumerate(split_key(key)):
            if j > 0:
                tk.Label(key_row, text="→", font=(UI_FONT, key_font, "bold"),
                         bg=c["bg_card"], fg=c["accent"]).pack(side="left", padx=3)
            for i, k in enumerate(keys):
                if i > 0:
                    tk.Label(key_row, text="+", font=(MONO_FONT, max(7, key_font - 1), "bold"),
                             bg=c["bg_card"], fg=c["text_dim"]).pack(side="left", padx=1)
                self._draw_key_cap(key_row, k, c, key_font)

        tk.Frame(card, bg=c["border"], height=1).pack(fill="x", padx=6)

        desc_font = self._fs(10 if is_widget else 12)
        tk.Label(card, text=desc, font=(UI_FONT, desc_font),
                 bg=c["bg_card"], fg=c["text_dim"], anchor="w",
                 justify="left").pack(fill="x", padx=10, pady=(6, 8))

    def _draw_info_icon(self, parent, key, info):
        c = self.c
        cv = tk.Canvas(parent, width=16, height=16, bg=c["bg_card"],
                       highlightthickness=0, cursor="question_arrow")
        cv.create_oval(1, 1, 15, 15, fill=c["key_bg"], outline=c["key_border"])
        cv.create_text(8, 8, text="i", font=(UI_FONT, 8, "bold"), fill=c["key_text"])
        cv.pack(side="right", padx=(4, 0))
        Tooltip(cv, lambda: key, lambda: info, lambda: self.c)

    def _draw_key_cap(self, parent, text, c, font_size=11):
        test = tk.Label(parent, text=text, font=(MONO_FONT, font_size, "bold"),
                        bg=c["bg_card"], fg=c["key_text"])
        tw = test.winfo_reqwidth() + 20
        test.destroy()
        th = int(font_size * 2 + 8)
        r = 5

        canvas = tk.Canvas(parent, width=tw, height=th,
                           bg=c["bg_card"], highlightthickness=0)
        canvas.pack(side="left", padx=1)

        self._rounded_rect(canvas, 1, 1, tw, th, r, c["border"])
        self._rounded_rect(canvas, 0, 0, tw - 1, th - 1, r, c["key_bg"])
        self._rounded_rect(canvas, 1, 1, tw - 2, th // 2, r, c.get("key_highlight", c["key_bg"]))
        canvas.create_text(tw // 2, th // 2, text=text,
                           font=(MONO_FONT, font_size, "bold"), fill=c["key_text"],
                           anchor="center")

    def _rounded_rect(self, canvas, x1, y1, x2, y2, r, fill):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, fill=fill, outline="")

    def _bind_wheel(self, canvas, widget):
        def on_wheel(e):
            if e.delta:
                canvas.yview_scroll(-1 if e.delta > 0 else 1, "units")
        widget.bind("<MouseWheel>", on_wheel)
        for child in widget.winfo_children():
            self._bind_wheel(canvas, child)

    def _update_shortcuts(self, app_name):
        self._clear_shortcuts()
        shortcuts = self.shortcut_data[self._lookup(app_name)]
        display_name = shortcuts.get("name", app_name)
        items = shortcuts.get("shortcuts", [])
        self.app_label.config(text=display_name)

        if not items:
            tk.Label(self.container, text="Nenhum atalho mapeado",
                     font=(UI_FONT, 14), bg=self.c["bg"],
                     fg=self.c["text_dim"]).pack(expand=True)
            return

        display = self.settings.get("display", "fullscreen")
        if display == "widget":
            ww = self.root.winfo_width()
            cols = max(2, min(4, ww // 190))
        else:
            ww = self.root.winfo_width()
            cols = max(2, min(6, ww // 280))

        canvas = tk.Canvas(self.container, bg=self.c["bg"], highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        wrapper = tk.Frame(canvas, bg=self.c["bg"])
        win_id = canvas.create_window((0, 0), window=wrapper, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win_id, width=e.width))
        wrapper.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        for i, item in enumerate(items):
            row, col = divmod(i, cols)
            self._make_card(wrapper, item, row, col, display)
        for c in range(cols):
            wrapper.columnconfigure(c, weight=1)
        self._bind_wheel(canvas, wrapper)
        self._bind_drag_tree(self.root)

    def _poll_focus(self):
        try:
            exe = get_foreground_exe()
            if exe and exe != self._current_app:
                self._current_app = exe
                self._update_shortcuts(exe)
        except Exception:
            pass
        self.root.after(400, self._poll_focus)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    if tk is None:
        sys.exit("tkinter indisponivel: instale python3-tk (Linux) ou o Python do python.org (macOS)")
    app = ShortcutsWindow()
    app.run()
