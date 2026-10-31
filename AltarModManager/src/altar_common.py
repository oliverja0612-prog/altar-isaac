"""Shared pieces for the Altar manager and installer: theme, widgets, paths,
config and Isaac install detection."""
import json
import os
import re
import sys
import tkinter as tk

APP_NAME = "Altar"
VERSION = "1.0.0"
GITHUB_REPO = "oliverja0612-prog/altar-isaac"  # releases feed the Mod Manager's auto-update


def parse_version(v):
    """'v1.0.0' -> (1, 0, 0); anything unparsable sorts lowest."""
    try:
        return tuple(int(x) for x in str(v).lstrip("vV").split("."))
    except ValueError:
        return (0,)
GAME_EXE_NAME = "isaac-ng.exe"
MOD_FOLDER = "altar_core"

# ---------------------------------------------------------------- paths

FROZEN = getattr(sys, "frozen", False)
# Bundled read-only data (assets, payload) lives next to the source, or in the
# PyInstaller temp dir when running as an exe.
BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(BUNDLE_DIR, "assets")
EXE_DIR = os.path.dirname(sys.executable if FROZEN else os.path.abspath(__file__))

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
INSTALL_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "Programs", APP_NAME)


def load_config():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def is_game_dir(path):
    return bool(path) and os.path.isfile(os.path.join(path, GAME_EXE_NAME))


def steam_libraries():
    """Steam library roots from the registry and libraryfolders.vdf."""
    roots = []
    try:
        import winreg
        for hive, key in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for name in ("SteamPath", "InstallPath"):
                        try:
                            roots.append(winreg.QueryValueEx(k, name)[0])
                        except OSError:
                            pass
            except OSError:
                pass
    except ImportError:
        pass
    roots += [r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"]
    libs = []
    for root in roots:
        root = os.path.normpath(root)
        if root not in libs and os.path.isdir(root):
            libs.append(root)
        vdf = os.path.join(root, "steamapps", "libraryfolders.vdf")
        try:
            with open(vdf, encoding="utf-8", errors="replace") as f:
                for m in re.finditer(r'"path"\s+"([^"]+)"', f.read()):
                    p = os.path.normpath(m.group(1).replace("\\\\", "\\"))
                    if p not in libs:
                        libs.append(p)
        except OSError:
            pass
    return libs


def find_game_dirs(extra=()):
    """Every Isaac install we can find, best guess first."""
    found = []

    def add(p):
        if p and is_game_dir(p):
            p = os.path.normpath(p)
            if p not in found:
                found.append(p)

    for p in extra:
        add(p)
    add(load_config().get("game_dir"))
    # running from <game>/AltarModManager/ (or next to the game exe)
    add(os.path.dirname(EXE_DIR))
    add(EXE_DIR)
    for lib in steam_libraries():
        add(os.path.join(lib, "steamapps", "common", "The Binding of Isaac Rebirth"))
    for drive in "CDEFG":
        for sub in (r"Games\The Binding of Isaac Rebirth", r"SteamLibrary\steamapps\common\The Binding of Isaac Rebirth"):
            add(f"{drive}:\\{sub}")
    # Downloads folders with an Isaac build in them
    downloads = os.path.join(os.path.expanduser("~"), "Downloads")
    try:
        for name in os.listdir(downloads):
            if "isaac" in name.lower():
                base = os.path.join(downloads, name)
                add(base)
                try:
                    for sub in os.listdir(base):
                        add(os.path.join(base, sub))
                except OSError:
                    pass
    except OSError:
        pass
    return found


# ---------------------------------------------------------------- theme

BG = "#120d1c"
PANEL = "#1c1430"
CARD = "#2a1f45"
CARD_HI = "#36295a"
BORDER = "#3d2f66"
ACCENT = "#a866ff"
GOLD = "#ffc640"
GREEN = "#59ff80"
RED = "#ff5a66"
TEXT = "#f4efff"
SUB = "#a39bb8"
DIM = "#6b6385"
FONT = "Segoe UI"


def lighten(hexc, t):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(c + (255 - c) * t) for c in (r, g, b))


def darken(hexc, t):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(int(c * (1 - t)) for c in (r, g, b))


def blend(a, b, t):
    ra, ga, ba = (int(a[i:i + 2], 16) for i in (1, 3, 5))
    rb, gb, bb = (int(b[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(ra + (rb - ra) * t), int(ga + (gb - ga) * t), int(ba + (bb - ba) * t))


def rounded(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class PillButton(tk.Canvas):
    """Rounded button with an animated hover fade."""

    def __init__(self, master, text, command, color=ACCENT, fg=BG, width=110, height=32, bg=PANEL, font_size=10):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0, cursor="hand2")
        self.command, self.color, self.fg, self.text = command, color, fg, text
        self.w, self.h, self.font_size = width, height, font_size
        self.t = 0.0
        self.target = 0.0
        self.enabled = True
        self.draw()
        self.bind("<Enter>", lambda e: self._hover(1.0))
        self.bind("<Leave>", lambda e: self._hover(0.0))
        self.bind("<Button-1>", self._click)

    def _hover(self, target):
        self.target = target
        self._step()

    def _step(self):
        if abs(self.t - self.target) < 0.05:
            self.t = self.target
            self.draw()
            return
        self.t += (self.target - self.t) * 0.35
        self.draw()
        self.after(16, self._step)

    def _click(self, _):
        if self.enabled:
            self.command()

    def set_enabled(self, on):
        self.enabled = on
        self.configure(cursor="hand2" if on else "arrow")
        self.draw()

    def set_text(self, text):
        self.text = text
        self.draw()

    def draw(self):
        self.delete("all")
        base = self.color if self.enabled else "#4a3f63"
        c = blend(base, lighten(base, 0.2), self.t)
        lift = round(self.t)
        rounded(self, 1, 3, self.w - 1, self.h - 1, 12, fill=darken(base, 0.45))
        rounded(self, 1, 2 - lift, self.w - 1, self.h - 2 - lift, 12, fill=c)
        self.create_text(self.w / 2, self.h / 2 - 1 - lift, text=self.text, fill=self.fg if self.enabled else SUB,
                         font=(FONT, self.font_size, "bold"))


class Toggle(tk.Canvas):
    """iOS-style switch that slides when flipped."""

    def __init__(self, master, on, command, bg=CARD):
        super().__init__(master, width=46, height=24, bg=bg, highlightthickness=0, cursor="hand2")
        self.on, self.command = on, command
        self.pos = 1.0 if on else 0.0
        self.draw()
        self.bind("<Button-1>", self.flip)

    def flip(self, _=None):
        self.on = not self.on
        self._slide()
        self.command(self.on)

    def _slide(self):
        target = 1.0 if self.on else 0.0
        self.pos += (target - self.pos) * 0.4
        if abs(target - self.pos) < 0.03:
            self.pos = target
        self.draw()
        if self.pos != target:
            self.after(16, self._slide)

    def draw(self):
        self.delete("all")
        rounded(self, 2, 3, 44, 21, 9, fill=blend("#4a3f63", GREEN, self.pos))
        x = 13 + 20 * self.pos
        self.create_oval(x - 8, 4, x + 8, 20, fill=TEXT, outline="")


def letter_tile(master, name, size, bg):
    import colorsys
    c = tk.Canvas(master, width=size, height=size, bg=bg, highlightthickness=0)
    hue = (ord(name[:1] or "A") * 37) % 360
    r, g, b = colorsys.hsv_to_rgb(hue / 360, 0.55, 0.9)
    col = "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))
    rounded(c, 1, 1, size - 1, size - 1, 10, fill=col)
    c.create_text(size / 2, size / 2, text=name[:1].upper(), fill=BG, font=(FONT, int(size * 0.42), "bold"))
    return c


def set_window_icon(root):
    ico = os.path.join(ASSETS, "altar.ico")
    if os.path.isfile(ico):
        try:
            root.iconbitmap(default=ico)
            return
        except tk.TclError:
            pass
    png = os.path.join(ASSETS, "icon.png")
    if os.path.isfile(png):
        root.iconphoto(True, tk.PhotoImage(file=png))


def dark_title_bar(root):
    """Ask Windows 10/11 for a dark title bar so the window matches the theme."""
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new, old)
            if ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)) == 0:
                break
    except Exception:
        pass
