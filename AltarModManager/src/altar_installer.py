"""AltarSetup - a Geode-style installer for Altar (mod + manager app).

Wizard:  Welcome > Game folder > Options > Installing (progress bar) > Done
It copies the Altar Core mod into <game>/mods, installs Altar.exe to
%LOCALAPPDATA%\\Programs\\Altar, adds shortcuts and an "Apps & features" entry.

    AltarSetup.exe                 run the wizard
    AltarSetup.exe --uninstall     remove Altar (used by Apps & features)
    AltarSetup.exe --update        update in place (launched by the Mod Manager's auto-update)
    AltarSetup.exe --silent --game <dir> [--app-dir <dir>] [--no-shortcuts] [--no-registry]
"""
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import zipfile
from tkinter import filedialog

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from altar_sounds import write_sounds_xml  # noqa: E402
from altar_common import (  # noqa: E402
    ACCENT, APP_NAME, ASSETS, BG, BORDER, BUNDLE_DIR, CARD, CARD_HI, CONFIG_DIR, DIM, FONT, FROZEN, GOLD, GREEN,
    INSTALL_DIR, MOD_FOLDER, PANEL, RED, SUB, TEXT, VERSION, PillButton, Toggle, blend, dark_title_bar,
    find_game_dirs, is_game_dir, load_config, rounded, save_config, set_window_icon,
)

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = ImageTk = None

# voice files that are only ever installed locally (see tools/build.py --public)
VOICE_PATHS = (os.path.join("sfx", "altar"), os.path.join("resources", "sfx", "altar"))
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\AltarModManager"
NO_WINDOW = 0x08000000


def payload_path():
    for p in (os.path.join(BUNDLE_DIR, "payload.zip"), os.path.join(BUNDLE_DIR, "build", "payload.zip")):
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------- install steps

def powershell(script):
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                   creationflags=NO_WINDOW, capture_output=True, timeout=30)


def ps_quote(s):
    return "'" + s.replace("'", "''") + "'"


def make_shortcuts(target, icon, desktop=True, start_menu=True):
    parts = []
    for enabled, folder in ((desktop, "Desktop"), (start_menu, "Programs")):
        if enabled:
            parts.append(
                f"$p=Join-Path ([Environment]::GetFolderPath('{folder}')) 'Altar.lnk';"
                f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut($p);"
                f"$s.TargetPath={ps_quote(target)};$s.IconLocation={ps_quote(icon)};"
                f"$s.WorkingDirectory={ps_quote(os.path.dirname(target))};"
                f"$s.Description='Altar Mod Manager';$s.Save();")
    if parts:
        powershell("".join(parts))


def remove_shortcuts():
    powershell("foreach($f in 'Desktop','Programs'){$p=Join-Path ([Environment]::GetFolderPath($f)) 'Altar.lnk';"
               "if(Test-Path $p){Remove-Item $p -Force}}")


def register_uninstaller(app_dir, size_kb):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as k:
        exe = os.path.join(app_dir, "Altar.exe")
        values = {
            "DisplayName": "Altar Mod Manager",
            "DisplayVersion": VERSION,
            "Publisher": "Altar",
            "DisplayIcon": exe,
            "InstallLocation": app_dir,
            "UninstallString": f'"{os.path.join(app_dir, "Uninstall Altar.exe")}" --uninstall',
        }
        for name, v in values.items():
            winreg.SetValueEx(k, name, 0, winreg.REG_SZ, v)
        winreg.SetValueEx(k, "EstimatedSize", 0, winreg.REG_DWORD, int(size_kb))
        winreg.SetValueEx(k, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(k, "NoRepair", 0, winreg.REG_DWORD, 1)


def unregister_uninstaller():
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except OSError:
        pass


def install(game_dir, app_dir=INSTALL_DIR, shortcuts=(True, True), registry=True, progress=lambda f, msg: None):
    """Copy everything into place. progress(fraction, message) is called as it goes."""
    payload = payload_path()
    if not payload:
        raise RuntimeError("Installer payload is missing (payload.zip). Rebuild with tools/build.py.")
    mod_dir = os.path.join(game_dir, "mods", MOD_FOLDER)
    with zipfile.ZipFile(payload) as z:
        entries = [i for i in z.infolist() if not i.is_dir()]
        total = sum(i.file_size for i in entries) or 1
        done = 0
        # public builds ship without the voice lines: keep any local ones across updates
        kept = None
        if not any(n.startswith("mod/resources/sfx/altar/") for n in z.namelist()) and os.path.isdir(mod_dir):
            kept = tempfile.mkdtemp(prefix="altar_keep_")
            for rel in VOICE_PATHS:
                src = os.path.join(mod_dir, rel)
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(os.path.join(kept, rel)), exist_ok=True)
                    shutil.move(src, os.path.join(kept, rel))
        progress(0.02, "Removing old Altar Core...")
        if os.path.isdir(mod_dir):
            shutil.rmtree(mod_dir)
        os.makedirs(app_dir, exist_ok=True)
        for info in entries:
            name = info.filename
            if name.startswith("mod/"):
                target = os.path.join(mod_dir, *name[4:].split("/"))
            elif name.startswith("app/"):
                target = os.path.join(app_dir, *name[4:].split("/"))
            else:
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            done += info.file_size
            progress(0.05 + 0.8 * done / total, name.split("/")[-1])
        if kept:
            for rel in VOICE_PATHS:
                src, dst = os.path.join(kept, rel), os.path.join(mod_dir, rel)
                if os.path.exists(src) and not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.move(src, dst)
            shutil.rmtree(kept, ignore_errors=True)
        write_sounds_xml(mod_dir)  # register whatever voice lines + SFX are now present
    # a copy of this installer doubles as the uninstaller
    if FROZEN:
        shutil.copy2(sys.executable, os.path.join(app_dir, "Uninstall Altar.exe"))
    progress(0.88, "Saving settings...")
    cfg = load_config()
    cfg["game_dir"] = os.path.normpath(game_dir)
    save_config(cfg)
    exe = os.path.join(app_dir, "Altar.exe")
    if any(shortcuts):
        progress(0.92, "Creating shortcuts...")
        make_shortcuts(exe, exe, *shortcuts)
    if registry:
        progress(0.97, "Registering in Apps & features...")
        size_kb = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(app_dir) for f in fs) // 1024
        register_uninstaller(app_dir, size_kb)
    progress(1.0, "Done")
    return exe


def uninstall(remove_mod=True, progress=lambda f, msg: None):
    game_dir = load_config().get("game_dir")
    progress(0.2, "Removing shortcuts...")
    remove_shortcuts()
    progress(0.4, "Removing Apps & features entry...")
    unregister_uninstaller()
    if remove_mod and game_dir:
        progress(0.6, "Removing Altar Core mod...")
        shutil.rmtree(os.path.join(game_dir, "mods", MOD_FOLDER), ignore_errors=True)
    progress(0.8, "Removing app files...")
    me = os.path.normcase(os.path.abspath(sys.executable))
    if os.path.isdir(INSTALL_DIR):
        for f in os.listdir(INSTALL_DIR):
            p = os.path.join(INSTALL_DIR, f)
            if os.path.normcase(os.path.abspath(p)) != me:
                shutil.rmtree(p, ignore_errors=True) if os.path.isdir(p) else _try_remove(p)
    shutil.rmtree(CONFIG_DIR, ignore_errors=True)
    progress(1.0, "Done")


def _try_remove(p):
    try:
        os.remove(p)
    except OSError:
        pass


def schedule_self_delete():
    """The running uninstaller can't delete itself, so a hidden cmd does it after exit."""
    if FROZEN and os.path.normcase(os.path.dirname(sys.executable)) == os.path.normcase(INSTALL_DIR):
        subprocess.Popen(f'cmd /c ping 127.0.0.1 -n 3 > nul & rmdir /s /q "{INSTALL_DIR}"',
                         creationflags=NO_WINDOW, shell=False)


# ---------------------------------------------------------------- widgets

class ProgressBar(tk.Canvas):
    """Rounded gradient bar that eases toward its value with a moving shine."""

    def __init__(self, master, width=520, height=22, bg=BG):
        super().__init__(master, width=width, height=height, bg=bg, highlightthickness=0)
        self.w, self.h = width, height
        self.value = 0.0
        self.shown = 0.0
        self.phase = 0.0
        self._tick()

    def set(self, v):
        self.value = max(0.0, min(1.0, v))

    def _tick(self):
        self.shown += (self.value - self.shown) * 0.12
        self.phase = (self.phase + 0.02) % 1.0
        self.draw()
        self.after(16, self._tick)

    def draw(self):
        self.delete("all")
        w, h = self.w, self.h
        r = h // 2
        rounded(self, 0, 0, w, h, r, fill=CARD, outline=BORDER)
        if self.shown < 0.005:
            return
        fw = max(h, int(w * self.shown))
        # gradient keyed to absolute position, so the colour under the tip
        # always matches how far along the install is
        x = 3
        while x < fw - 3:
            x1 = min(fw - 3, x + 6)
            self.create_rectangle(x, 3, x1, h - 3, fill=blend(ACCENT, GOLD, x / w), outline="")
            x = x1
        self.create_oval(2, 3, h - 4, h - 3, fill=ACCENT, outline="")
        self.create_oval(fw - h + 4, 3, fw - 2, h - 3, fill=blend(ACCENT, GOLD, fw / w), outline="")
        # soft highlight across the top and a shine band sweeping along
        self.create_line(r, 5, fw - r, 5, fill=blend(blend(ACCENT, GOLD, self.shown / 2), "#ffffff", 0.35))
        sx = (fw + 80) * self.phase - 40
        for k, a in enumerate((0.12, 0.22, 0.3, 0.22, 0.12)):
            bx = sx + k * 6
            if r < bx < fw - r - 6:
                self.create_rectangle(bx, 3, bx + 6, h - 3, fill=blend(blend(ACCENT, GOLD, bx / w), "#ffffff", a),
                                      outline="")


class StepDots(tk.Canvas):
    def __init__(self, master, steps, bg=PANEL):
        super().__init__(master, width=steps * 18, height=12, bg=bg, highlightthickness=0)
        self.steps = steps
        self.set(0)

    def set(self, i):
        self.delete("all")
        for k in range(self.steps):
            x = 6 + k * 18
            if k == i:
                rounded(self, x - 6, 2, x + 10, 10, 4, fill=ACCENT)
            else:
                self.create_oval(x - 3, 3, x + 3, 9, fill=ACCENT if k < i else BORDER, outline="")


# ---------------------------------------------------------------- wizard

class Wizard(tk.Tk):
    W, H = 680, 520

    def __init__(self, mode="install"):
        super().__init__()
        self.mode = mode
        self.title({"install": "Altar Setup", "update": "Updating Altar"}.get(mode, "Uninstall Altar"))
        self.geometry(f"{self.W}x{self.H}")
        self.resizable(False, False)
        self.configure(bg=BG)
        set_window_icon(self)
        dark_title_bar(self)
        self.images = []
        self.game_dir = tk.StringVar()
        self.opt_desktop = True
        self.opt_start = True
        self.opt_launch = True
        self.opt_remove_mod = True
        self.result_exe = None
        self.error = None
        self._center()
        self.build_chrome()
        if mode == "update":  # launched by the Mod Manager: straight to installing
            self.pages = ["installing", "done"]
            found = find_game_dirs()
            self.game_dir.set(load_config().get("game_dir") or (found[0] if found else ""))
        elif mode == "install":
            self.pages = ["welcome", "location", "options", "installing", "done"]
        else:
            self.pages = ["confirm", "installing", "done"]
        self.page_i = 0
        self.show()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.W) // 2
        y = (self.winfo_screenheight() - self.H) // 3
        self.geometry(f"+{x}+{y}")

    def photo(self, path, size=None, smooth=True):
        if Image is None or not os.path.isfile(path):
            return None
        im = Image.open(path).convert("RGBA")
        if size:
            im = im.resize(size, Image.LANCZOS if smooth else Image.NEAREST)
        p = ImageTk.PhotoImage(im)
        self.images.append(p)
        return p

    # ---------------- chrome
    def build_chrome(self):
        self.banner = tk.Canvas(self, width=self.W, height=130, bg=BG, highlightthickness=0)
        self.banner.pack(fill="x")
        b = self.photo(os.path.join(ASSETS, "banner.png"), (self.W, 150))
        if b:
            self.banner.create_image(0, -10, image=b, anchor="nw")
        logo = self.photo(os.path.join(ASSETS, "app_icon.png"), (76, 76))
        if logo:
            self.banner.create_image(28, 27, image=logo, anchor="nw")
        self.banner.create_text(118, 46, text="ALTAR", fill=TEXT, font=(FONT, 28, "bold"), anchor="w")
        sub = "Setup" if self.mode != "uninstall" else "Uninstall"
        self.banner.create_text(120, 82, text=f"{sub}  •  v{VERSION}", fill=SUB, font=(FONT, 11), anchor="w")
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        # footer is packed before the body so tall pages can never push it down
        foot = tk.Frame(self, bg=PANEL, height=64)
        foot.pack(fill="x", side="bottom")
        foot.pack_propagate(False)

        self.body = tk.Frame(self, bg=BG)
        self.body.pack(fill="both", expand=True, padx=34, pady=(22, 0))
        self.dots = StepDots(foot, {"install": 5, "update": 2}.get(self.mode, 3))
        self.dots.pack(side="left", padx=24)
        self.next_btn = PillButton(foot, "Next  ›", self.next, width=120, height=36)
        self.next_btn.pack(side="right", padx=(6, 20))
        self.back_btn = PillButton(foot, "‹  Back", self.back, color=CARD_HI, fg=TEXT, width=100, height=36)
        self.back_btn.pack(side="right")
        self.cancel_btn = PillButton(foot, "Cancel", self.destroy, color=PANEL, fg=SUB, width=86, height=36)
        self.cancel_btn.pack(side="right", padx=6)

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def heading(self, title, sub=None):
        tk.Label(self.body, text=title, fg=TEXT, bg=BG, font=(FONT, 17, "bold")).pack(anchor="w")
        if sub:
            tk.Label(self.body, text=sub, fg=SUB, bg=BG, font=(FONT, 10), wraplength=600, justify="left").pack(
                anchor="w", pady=(2, 14))

    def show(self):
        self.clear()
        name = self.pages[self.page_i]
        self.dots.set(self.page_i)
        self.back_btn.set_enabled(0 < self.page_i and name not in ("installing", "done"))
        self.cancel_btn.set_enabled(name not in ("installing", "done"))
        getattr(self, "page_" + name)()
        self.fade_in()

    def fade_in(self, step=0):
        """Slide the page content in from the right."""
        if step == 0:
            self.body.pack_configure(padx=(64, 4))
        pad = int(30 * (1 - min(1, step / 8)) ** 2)
        self.body.pack_configure(padx=(34 + pad, 34 - pad))
        if step < 8:
            self.after(16, lambda: self.fade_in(step + 1))

    def next(self):
        name = self.pages[self.page_i]
        if name == "location" and not is_game_dir(self.game_dir.get()):
            self.loc_status.configure(text="✖  Pick the folder that contains isaac-ng.exe", fg=RED)
            return
        if name == "done":
            if self.mode != "uninstall" and self.opt_launch and self.result_exe:
                subprocess.Popen([self.result_exe], cwd=os.path.dirname(self.result_exe))
            if self.mode == "uninstall":
                schedule_self_delete()
            self.destroy()
            return
        self.page_i += 1
        self.show()

    def back(self):
        if self.page_i > 0:
            self.page_i -= 1
            self.show()

    # ---------------- pages
    def page_welcome(self):
        self.heading("Welcome to Altar", "This will install the Altar Core mod into The Binding of Isaac and the "
                                         "Altar Mod Manager app on this PC.")
        feats = [
            ("✦", "In-game menu", "F2 / gem button: items, hearts, combos, warps, debug tools"),
            ("⚡", "32 animated items", "Black holes, beams, combos and very broken builds"),
            ("⌨", "Command console", "F4: boss monstro, give overclock 3, tp devil, combo all..."),
            ("⚙", "Mod Manager", "Enable/disable mods, profiles, conflict checker, one-click Play"),
        ]
        for icon, title, desc in feats:
            row = tk.Frame(self.body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", pady=3)
            tk.Label(row, text=icon, fg=ACCENT, bg=CARD, font=(FONT, 15)).pack(side="left", padx=(12, 8), pady=6)
            tk.Label(row, text=title, fg=TEXT, bg=CARD, font=(FONT, 10, "bold"), width=16, anchor="w").pack(side="left")
            tk.Label(row, text=desc, fg=SUB, bg=CARD, font=(FONT, 9), anchor="w").pack(side="left")
        self.next_btn.set_text("Next  ›")

    def page_location(self):
        self.heading("Game folder", "Altar found these Isaac installs. Pick one, or browse to the folder with "
                                    "isaac-ng.exe in it.")
        found = find_game_dirs()
        if not self.game_dir.get() and found:
            self.game_dir.set(found[0])
        listf = tk.Frame(self.body, bg=BG)
        listf.pack(fill="x")
        self.loc_rows = []

        def paint():
            for path, row, labels in self.loc_rows:
                sel = os.path.normcase(path) == os.path.normcase(self.game_dir.get())
                row.configure(bg=CARD_HI if sel else CARD, highlightbackground=ACCENT if sel else BORDER)
                for lab in labels:
                    lab.configure(bg=CARD_HI if sel else CARD)
                labels[0].configure(text="◉" if sel else "○", fg=ACCENT if sel else DIM)
            ok = is_game_dir(self.game_dir.get())
            self.loc_status.configure(text=("✔  isaac-ng.exe found" if ok else "Choose a folder"),
                                      fg=GREEN if ok else SUB)

        for path in found[:4]:
            row = tk.Frame(listf, bg=CARD, highlightthickness=1, cursor="hand2")
            row.pack(fill="x", pady=3)
            dot = tk.Label(row, text="○", fg=DIM, bg=CARD, font=(FONT, 13))
            dot.pack(side="left", padx=(10, 6), pady=6)
            lab = tk.Label(row, text=path, fg=TEXT, bg=CARD, font=(FONT, 9), anchor="w")
            lab.pack(side="left", fill="x", expand=True)
            for w in (row, dot, lab):
                w.bind("<Button-1>", lambda e, p=path: (self.game_dir.set(p), paint()))
            self.loc_rows.append((path, row, [dot, lab]))
        if not found:
            tk.Label(listf, text="No install found automatically.", fg=DIM, bg=BG, font=(FONT, 10)).pack(anchor="w")

        pick = tk.Frame(self.body, bg=BG)
        pick.pack(fill="x", pady=(12, 0))
        entry = tk.Entry(pick, textvariable=self.game_dir, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                         font=(FONT, 10))
        entry.pack(side="left", fill="x", expand=True, ipady=7)
        entry.bind("<KeyRelease>", lambda e: paint())

        def browse():
            p = filedialog.askdirectory(title="Select your Isaac folder (contains isaac-ng.exe)")
            if p:
                self.game_dir.set(os.path.normpath(p))
                paint()
        PillButton(pick, "Browse...", browse, color=CARD_HI, fg=TEXT, width=100, height=32, bg=BG).pack(
            side="left", padx=(8, 0))
        self.loc_status = tk.Label(self.body, text="", fg=SUB, bg=BG, font=(FONT, 10, "bold"))
        self.loc_status.pack(anchor="w", pady=(8, 0))
        paint()
        self.next_btn.set_text("Next  ›")

    def option_row(self, text, sub, attr):
        row = tk.Frame(self.body, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        row.pack(fill="x", pady=3)
        t = tk.Frame(row, bg=CARD)
        t.pack(side="left", padx=12, pady=7)
        tk.Label(t, text=text, fg=TEXT, bg=CARD, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(t, text=sub, fg=SUB, bg=CARD, font=(FONT, 9)).pack(anchor="w")
        Toggle(row, getattr(self, attr), lambda on: setattr(self, attr, on)).pack(side="right", padx=12)

    def page_options(self):
        self.heading("Options")
        tk.Frame(self.body, bg=BG, height=8).pack()
        self.option_row("Desktop shortcut", "Put an Altar icon on your desktop", "opt_desktop")
        self.option_row("Start menu shortcut", "Find Altar from the Start menu", "opt_start")
        self.option_row("Launch Altar when done", "Open the Mod Manager after installing", "opt_launch")
        info = tk.Frame(self.body, bg=BG)
        info.pack(fill="x", pady=(10, 0))
        tk.Label(info, text="Mod  →  " + os.path.join(self.game_dir.get(), "mods", MOD_FOLDER), fg=DIM, bg=BG,
                 font=(FONT, 8)).pack(anchor="w")
        tk.Label(info, text="App  →  " + INSTALL_DIR, fg=DIM, bg=BG, font=(FONT, 8)).pack(anchor="w")
        self.next_btn.set_text("Install")

    def page_confirm(self):
        self.heading("Uninstall Altar", "This removes the Altar Mod Manager app, its shortcuts and settings.")
        self.option_row("Also remove the Altar Core mod", "Deletes mods/" + MOD_FOLDER + " from your Isaac folder",
                        "opt_remove_mod")
        self.next_btn.set_text("Uninstall")

    def page_installing(self):
        self.heading("Installing..." if self.mode != "uninstall" else "Uninstalling...")
        self.bar = ProgressBar(self.body, width=self.W - 70)
        self.bar.pack(pady=(18, 8))
        row = tk.Frame(self.body, bg=BG)
        row.pack(fill="x")
        self.pct = tk.Label(row, text="0%", fg=TEXT, bg=BG, font=(FONT, 20, "bold"))
        self.pct.pack(side="left")
        self.status = tk.Label(row, text="Starting...", fg=SUB, bg=BG, font=(FONT, 10))
        self.status.pack(side="left", padx=12, pady=(8, 0))
        self.next_btn.set_enabled(False)
        self.next_btn.set_text("Next  ›")
        self.progress = (0.0, "Starting...")
        self.finished = False
        threading.Thread(target=self.worker, daemon=True).start()
        self.poll()

    def worker(self):
        def report(f, msg):
            self.progress = (f, msg)
            time.sleep(0.004)  # let the bar visibly fill even when copying is instant
        try:
            if self.mode != "uninstall":
                self.result_exe = install(self.game_dir.get(), shortcuts=(self.opt_desktop, self.opt_start),
                                          progress=report)
            else:
                uninstall(self.opt_remove_mod, progress=report)
        except Exception as e:  # shown on the done page
            self.error = str(e)
        self.finished = True

    def poll(self):
        f, msg = self.progress
        self.bar.set(f)
        self.pct.configure(text=f"{int(self.bar.shown * 100 + 0.5)}%")
        self.status.configure(text=msg[:60])
        if self.finished and (self.error or self.bar.shown > 0.985):
            self.after(350, self.next)
            return
        self.after(30, self.poll)

    def page_done(self):
        ok = self.error is None
        c = tk.Canvas(self.body, width=96, height=96, bg=BG, highlightthickness=0)
        c.pack(pady=(4, 6))
        tk.Label(self.body, text=("Altar is installed!" if self.mode != "uninstall" else "Altar was removed.") if ok
                 else "Something went wrong", fg=TEXT, bg=BG, font=(FONT, 18, "bold")).pack()
        if ok and self.mode != "uninstall":
            msg = "Start Isaac and press F2 in a run (or click the gem in the corner).\nF4 opens the command console."
        elif ok:
            msg = "Thanks for trying Altar."
        else:
            msg = self.error
        tk.Label(self.body, text=msg, fg=SUB if ok else RED, bg=BG, font=(FONT, 10), justify="center",
                 wraplength=580).pack(pady=6)
        self.animate_badge(c, ok)
        self.next_btn.set_enabled(True)
        self.next_btn.set_text("Launch Altar" if ok and self.mode != "uninstall" and self.opt_launch else "Finish")

    def animate_badge(self, c, ok, step=0):
        c.delete("all")
        t = min(1, step / 18)
        e = 1 + 2.2 * (t - 1) ** 3 + 1.2 * (t - 1) ** 2  # ease out back
        r = 40 * e
        col = GREEN if ok else RED
        c.create_oval(48 - r - 6, 48 - r - 6, 48 + r + 6, 48 + r + 6, fill=blend(BG, col, 0.18), outline="")
        c.create_oval(48 - r, 48 - r, 48 + r, 48 + r, fill=col, outline="")
        if t > 0.5:
            k = (t - 0.5) * 2
            if ok:
                pts = [(30, 50), (43, 62), (68, 36)]
                x1 = pts[1][0] + (pts[2][0] - pts[1][0]) * k
                y1 = pts[1][1] + (pts[2][1] - pts[1][1]) * k
                c.create_line(pts[0], pts[1], (x1, y1), fill=BG, width=8, capstyle="round", joinstyle="round")
            else:
                d = 14 * k
                c.create_line(48 - d, 48 - d, 48 + d, 48 + d, fill=BG, width=8, capstyle="round")
                c.create_line(48 + d, 48 - d, 48 - d, 48 + d, fill=BG, width=8, capstyle="round")
        if step < 18:
            self.after(16, lambda: self.animate_badge(c, ok, step + 1))


def main():
    args = sys.argv[1:]

    def opt(name):
        return args[args.index(name) + 1] if name in args else None

    if "--silent" in args:
        game = opt("--game") or (find_game_dirs() or [None])[0]
        if not is_game_dir(game):
            print("No Isaac folder found; pass --game <dir>")
            sys.exit(1)
        exe = install(game, app_dir=opt("--app-dir") or INSTALL_DIR,
                      shortcuts=(False, False) if "--no-shortcuts" in args else (True, True),
                      registry="--no-registry" not in args,
                      progress=lambda f, msg: print(f"{int(f * 100):3d}%  {msg}"))
        print("Installed:", exe)
        return
    mode = "uninstall" if "--uninstall" in args else "update" if "--update" in args else "install"
    Wizard(mode).mainloop()


if __name__ == "__main__":
    main()
