"""Altar Mod Manager - a mod manager for The Binding of Isaac: Repentance(+).

Mods are enabled/disabled the same way the game does it: a `disable.it` file
inside the mod folder means disabled. Every change also rewrites
mods/altar_core/altar_modlist.lua so the in-game Altar menu can show the list.

Runs from source (python src/altar_manager.py) or as the bundled Altar.exe.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import tkinter as tk
import xml.etree.ElementTree as ET
import zipfile
from tkinter import filedialog, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from altar_common import (  # noqa: E402
    ACCENT, ASSETS, GITHUB_REPO, parse_version, BG, BORDER, CARD, CARD_HI, CONFIG_DIR, DIM, FONT, GAME_EXE_NAME, GOLD, GREEN, MOD_FOLDER,
    PANEL, RED, SUB, TEXT, VERSION, PillButton, Toggle, dark_title_bar, find_game_dirs, is_game_dir,
    letter_tile, load_config, save_config, set_window_icon,
)

try:
    from PIL import Image, ImageTk
except ImportError:  # app still works, just without thumbnails
    Image = ImageTk = None

PROFILES_KEY = "profiles"
REMOVED_DIR = os.path.join(CONFIG_DIR, "removed_mods")


# ---------------------------------------------------------------- model

class Game:
    """Paths for one Isaac install."""

    def __init__(self, root):
        self.root = root
        self.exe = os.path.join(root, GAME_EXE_NAME)
        self.mods = os.path.join(root, "mods")
        self.modlist = os.path.join(self.mods, MOD_FOLDER, "altar_modlist.lua")


class Mod:
    def __init__(self, game, folder):
        self.folder = folder
        self.path = os.path.join(game.mods, folder)
        self.name = folder
        self.version = "?"
        self.description = ""
        self.workshop_id = ""
        self._read_metadata()

    def _read_metadata(self):
        meta = os.path.join(self.path, "metadata.xml")
        if not os.path.isfile(meta):
            return
        try:
            root = ET.parse(meta).getroot()
        except ET.ParseError:
            try:  # some workshop files have stray bytes; retry leniently
                with open(meta, "rb") as f:
                    root = ET.fromstring(f.read().decode("utf-8", "replace").encode("utf-8"))
            except Exception:
                return
        self.name = (root.findtext("name") or self.folder).strip()
        self.version = (root.findtext("version") or "?").strip()
        self.description = " ".join((root.findtext("description") or "").split())
        self.workshop_id = (root.findtext("id") or "").strip()

    @property
    def enabled(self):
        return not os.path.exists(os.path.join(self.path, "disable.it"))

    def set_enabled(self, on):
        flag = os.path.join(self.path, "disable.it")
        if on and os.path.exists(flag):
            os.remove(flag)
        elif not on and not os.path.exists(flag):
            open(flag, "w").close()

    @property
    def thumb(self):
        for n in ("thumb.png", "thumbnail.png", "icon.png"):
            p = os.path.join(self.path, n)
            if os.path.isfile(p):
                return p
        return None

    def files(self):
        out = []
        for root, _, names in os.walk(self.path):
            for n in names:
                out.append(os.path.relpath(os.path.join(root, n), self.path).replace("\\", "/"))
        return out

    def stats(self):
        files, size = 0, 0
        for root, _, names in os.walk(self.path):
            for n in names:
                files += 1
                try:
                    size += os.path.getsize(os.path.join(root, n))
                except OSError:
                    pass
        return files, size

    @property
    def kind(self):
        tags = []
        if os.path.isfile(os.path.join(self.path, "main.lua")):
            tags.append("Lua")
        if os.path.isdir(os.path.join(self.path, "resources")):
            tags.append("Resources")
        if os.path.isdir(os.path.join(self.path, "content")):
            tags.append("Content")
        return tags


def scan_mods(game):
    os.makedirs(game.mods, exist_ok=True)
    mods = [Mod(game, d) for d in os.listdir(game.mods) if os.path.isdir(os.path.join(game.mods, d))]
    mods.sort(key=lambda m: m.name.lower())
    return mods


def find_conflicts(mods):
    """Files under resources/ or content/ that more than one enabled mod replaces."""
    owners = {}
    for m in mods:
        if not m.enabled:
            continue
        for f in m.files():
            if f.startswith("resources/") or f.startswith("content/"):
                # content xml files merge instead of overwrite, so skip them
                if f.startswith("content/") and f.endswith(".xml"):
                    continue
                owners.setdefault(f, []).append(m.name)
    return {f: o for f, o in owners.items() if len(o) > 1}


def lua_str(s):
    s = s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")
    return '"' + "".join(c if ord(c) >= 32 else " " for c in s) + '"'


def write_modlist(game, mods):
    if not os.path.isdir(os.path.dirname(game.modlist)):
        return
    lines = ["-- Generated by Altar Mod Manager. Do not edit.", "return {"]
    for m in mods:
        lines.append(
            "\t{ name = %s, version = %s, folder = %s, enabled = %s, description = %s },"
            % (lua_str(m.name), lua_str(m.version), lua_str(m.folder),
               "true" if m.enabled else "false", lua_str(m.description[:160]))
        )
    lines.append("}")
    with open(game.modlist, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def push_clipboard(game, text):
    """Write copied text into Altar Core's save data so Ctrl+V in game can read it.

    The mod keeps its settings in data/altar_core/save<slot>.dat (JSON); we only
    add/replace the "clip" key and leave everything else alone.
    """
    data_dir = os.path.join(game.root, "data", MOD_FOLDER)
    os.makedirs(data_dir, exist_ok=True)
    files = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if re.fullmatch(r"save\d\.dat", f)]
    if not files:
        files = [os.path.join(data_dir, f"save{i}.dat") for i in (1, 2, 3)]
    for path in files:
        data = {}
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue  # never clobber a file we can't read
        if not isinstance(data, dict):
            continue
        data["clip"] = text[:400]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, separators=(",", ":"))


def human_size(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def resolve_game(arg=None):
    """Game folder from --game, config, auto-detect, or a folder picker."""
    candidates = find_game_dirs([arg] if arg else [])
    if candidates:
        return candidates[0]
    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Altar", "Couldn't find The Binding of Isaac automatically.\n\n"
                                 "Pick the folder that contains isaac-ng.exe.")
    while True:
        path = filedialog.askdirectory(title="Select your Isaac folder (contains isaac-ng.exe)")
        if not path:
            root.destroy()
            return None
        if is_game_dir(path):
            root.destroy()
            return os.path.normpath(path)
        messagebox.showerror("Altar", "That folder has no isaac-ng.exe. Try again.")


# ---------------------------------------------------------------- widgets

class ScrollFrame(tk.Frame):
    def __init__(self, master, bg):
        super().__init__(master, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.bar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=10)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self.win, width=e.width))
        self.canvas.configure(yscrollcommand=self.bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bar.pack(side="right", fill="y")
        self.bind_all("<MouseWheel>", self._wheel, add="+")

    def _wheel(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w is self:
                self.canvas.yview_scroll(int(-e.delta / 120) * 3, "units")
                return
            w = w.master

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


# ---------------------------------------------------------------- app

class App(tk.Tk):
    def __init__(self, game_dir):
        super().__init__()
        self.game = Game(game_dir)
        self.title("Altar Mod Manager")
        self.geometry("1100x700")
        self.minsize(920, 580)
        self.configure(bg=BG)
        set_window_icon(self)
        dark_title_bar(self)
        self.images = {}
        self.mods = []
        self.selected = None
        self.filter = tk.StringVar(value="all")
        self.search = tk.StringVar()
        self.search.trace_add("write", lambda *a: self.render_list())
        self.page = "installed"
        self.toast_after = None
        self.clip_link = load_config().get("clipboard_link", True)
        self.last_clip = None
        self.build()
        self.refresh()
        self.after(800, self.poll_clipboard)
        if load_config().get("auto_update", True):
            self.after(1500, self.check_for_update)

    # ---------------- auto-update from GitHub releases
    def check_for_update(self, manual=False):
        """Ask GitHub for the latest release in the background; offer it if it's newer."""
        def worker():
            try:
                req = urllib.request.Request(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                                             headers={"User-Agent": "Altar-Mod-Manager",
                                                      "Accept": "application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=8) as r:
                    rel = json.load(r)
            except Exception as e:
                if manual:
                    self.after(0, lambda: self.toast(f"Couldn't reach GitHub: {e}", RED))
                return
            tag = rel.get("tag_name", "")
            asset = next((a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".exe")), None)
            if asset and parse_version(tag) > parse_version(VERSION):
                self.after(0, lambda: self.offer_update(tag, asset))
            elif manual:
                self.after(0, lambda: self.toast(f"You're up to date (v{VERSION})"))
        threading.Thread(target=worker, daemon=True).start()

    def offer_update(self, tag, asset):
        size = asset.get("size", 0) / 1e6
        if not messagebox.askyesno("Altar update", f"Altar {tag} is out (you have v{VERSION}).\n\n"
                                                   f"Download it ({size:.0f} MB) and install now?"):
            self.toast(f"Update {tag} available - Settings > Check now", GOLD)
            return
        self.toast(f"Downloading {tag}...", GOLD)

        def worker():
            path = os.path.join(tempfile.gettempdir(), f"AltarSetup-{tag}.exe")
            try:
                req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": "Altar-Mod-Manager"})
                with urllib.request.urlopen(req, timeout=120) as r, open(path, "wb") as out:
                    shutil.copyfileobj(r, out)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Altar", f"Update download failed:\n{e}"))
                return
            self.after(0, lambda: self.run_update(path))
        threading.Thread(target=worker, daemon=True).start()

    def run_update(self, path):
        # the installer replaces Altar.exe, so this app has to close first
        subprocess.Popen([path, "--update"])
        self.destroy()

    def poll_clipboard(self):
        """Forward newly copied text to the game while the clipboard link is on."""
        try:
            if self.clip_link:
                try:
                    text = self.clipboard_get()
                except tk.TclError:  # clipboard empty or not text
                    text = None
                if text and text != self.last_clip and len(text) <= 2000:
                    if self.last_clip is not None:
                        push_clipboard(self.game, text)
                        self.toast("Copied to game - press Ctrl+V in the Altar console", ACCENT)
                    self.last_clip = text
        except OSError:
            pass
        finally:
            self.after(700, self.poll_clipboard)

    # ---------------- images
    def img(self, path, size, smooth=None):
        key = (path, size)
        if key not in self.images:
            if Image is None or not path:
                return None
            try:
                im = Image.open(path).convert("RGBA")
                pixel = im.width <= 64 if smooth is None else not smooth
                im = im.resize((size, size), Image.NEAREST if pixel else Image.LANCZOS)
                self.images[key] = ImageTk.PhotoImage(im)
            except Exception:
                self.images[key] = None
        return self.images[key]

    # ---------------- layout
    def build(self):
        header = tk.Frame(self, bg=PANEL, height=78)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(self, bg=ACCENT, height=2).pack(fill="x")

        logo = self.img(os.path.join(ASSETS, "logo.png"), 56, smooth=True)
        if logo:
            tk.Label(header, image=logo, bg=PANEL).pack(side="left", padx=(16, 8))
        title = tk.Frame(header, bg=PANEL)
        title.pack(side="left")
        tk.Label(title, text="ALTAR", fg=TEXT, bg=PANEL, font=(FONT, 22, "bold")).pack(anchor="w")
        tk.Label(title, text=f"Mod Manager for The Binding of Isaac  -  v{VERSION}", fg=SUB, bg=PANEL,
                 font=(FONT, 9)).pack(anchor="w")

        PillButton(header, "\u25B6  PLAY", self.launch, color=GOLD, width=130, height=42, font_size=13).pack(
            side="right", padx=16)
        self.count_lbl = tk.Label(header, text="", fg=SUB, bg=PANEL, font=(FONT, 10))
        self.count_lbl.pack(side="right", padx=8)
        self.toast_lbl = tk.Label(header, text="", fg=GREEN, bg=PANEL, font=(FONT, 10, "bold"))
        self.toast_lbl.pack(side="right", padx=8)

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        side = tk.Frame(body, bg=PANEL, width=180)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        self.nav = {}
        for key, label in (("installed", "Installed"), ("profiles", "Profiles"), ("conflicts", "Conflicts"),
                           ("items", "Altar Items"), ("settings", "Settings")):
            b = tk.Label(side, text="  " + label, anchor="w", fg=SUB, bg=PANEL, font=(FONT, 11, "bold"),
                         padx=14, pady=10, cursor="hand2")
            b.pack(fill="x", pady=(6 if key == "installed" else 0, 0))
            b.bind("<Button-1>", lambda e, k=key: self.show_page(k))
            b.bind("<Enter>", lambda e, w=b, k=key: w.configure(bg=CARD_HI) if self.page != k else None)
            b.bind("<Leave>", lambda e, w=b, k=key: w.configure(bg=CARD if self.page == k else PANEL))
            self.nav[key] = b
        tk.Frame(side, bg=PANEL).pack(fill="both", expand=True)
        self.game_lbl = tk.Label(side, text="", fg=DIM, bg=PANEL, font=(FONT, 8), wraplength=160, justify="left")
        self.game_lbl.pack(side="bottom", padx=10, pady=10, anchor="w")

        self.main = tk.Frame(body, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.details = tk.Frame(body, bg=PANEL, width=300)
        self.details.pack(side="right", fill="y")
        self.details.pack_propagate(False)
        self.show_page("installed")

    def toast(self, msg, color=GREEN):
        self.toast_lbl.configure(text=msg, fg=color)
        if self.toast_after:
            self.after_cancel(self.toast_after)
        self.toast_after = self.after(2500, lambda: self.toast_lbl.configure(text=""))

    def show_page(self, key):
        self.page = key
        for k, b in self.nav.items():
            b.configure(fg=TEXT if k == key else SUB, bg=CARD if k == key else PANEL)
        for w in self.main.winfo_children():
            w.destroy()
        getattr(self, "page_" + key)()

    def page_title(self, parent, title, sub):
        tk.Label(parent, text=title, fg=TEXT, bg=BG, font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(parent, text=sub, fg=SUB, bg=BG, font=(FONT, 9), wraplength=600, justify="left").pack(
            anchor="w", pady=(0, 10))

    # ---------------- installed page
    def page_installed(self):
        bar = tk.Frame(self.main, bg=BG)
        bar.pack(fill="x", padx=16, pady=(14, 8))
        box = tk.Frame(bar, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        box.pack(side="left", fill="x", expand=True)
        tk.Label(box, text="\U0001F50D", bg=CARD, fg=SUB).pack(side="left", padx=(8, 0))
        e = tk.Entry(box, textvariable=self.search, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                     font=(FONT, 11))
        e.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        e.bind("<FocusIn>", lambda ev: box.configure(highlightbackground=ACCENT))
        e.bind("<FocusOut>", lambda ev: box.configure(highlightbackground=BORDER))
        for val, label in (("all", "All"), ("on", "Enabled"), ("off", "Disabled")):
            tk.Radiobutton(bar, text=label, value=val, variable=self.filter, command=self.render_list,
                           indicatoron=False, bg=CARD, fg=TEXT, selectcolor=ACCENT, activebackground=CARD_HI,
                           activeforeground=TEXT, relief="flat", font=(FONT, 9, "bold"), padx=10, pady=6,
                           bd=0).pack(side="left", padx=(6, 0))

        actions = tk.Frame(self.main, bg=BG)
        actions.pack(fill="x", padx=16, pady=(0, 8))
        for text, cmd, col in (("Install .zip", self.install_zip, ACCENT),
                               ("Enable all", lambda: self.set_all(True), GREEN),
                               ("Disable all", lambda: self.set_all(False), RED),
                               ("Open folder", lambda: os.startfile(self.game.mods), CARD_HI),
                               ("Refresh", self.refresh, CARD_HI)):
            PillButton(actions, text, cmd, color=col, fg=TEXT if col == CARD_HI else BG, width=104, height=30,
                       bg=BG, font_size=9).pack(side="left", padx=(0, 6))

        self.list = ScrollFrame(self.main, BG)
        self.list.pack(fill="both", expand=True, padx=(16, 4), pady=(0, 12))
        self.render_list()

    def visible_mods(self):
        q = self.search.get().lower().strip()
        f = self.filter.get()
        out = []
        for m in self.mods:
            if q and q not in m.name.lower() and q not in m.folder.lower() and q not in m.description.lower():
                continue
            if f == "on" and not m.enabled or f == "off" and m.enabled:
                continue
            out.append(m)
        return out

    def render_list(self):
        if self.page != "installed" or not hasattr(self, "list"):
            return
        self.list.clear()
        mods = self.visible_mods()
        if not mods:
            tk.Label(self.list.inner, text="No mods found.\nDrop mod folders into the mods folder or use Install .zip.",
                     fg=SUB, bg=BG, font=(FONT, 11), pady=40).pack(fill="x")
        conflicted = {n for owners in find_conflicts(self.mods).values() for n in owners}
        for m in mods:
            self.mod_card(m, m.name in conflicted)

    def mod_card(self, m, conflicted):
        sel = self.selected is m
        card = tk.Frame(self.list.inner, bg=CARD_HI if sel else CARD, highlightthickness=1,
                        highlightbackground=ACCENT if sel else BORDER)
        card.pack(fill="x", pady=4, padx=(0, 8))
        bg = card["bg"]

        thumb = self.img(m.thumb, 48) if m.thumb else None
        icon = tk.Label(card, image=thumb, bg=bg) if thumb else letter_tile(card, m.name, 48, bg)
        icon.pack(side="left", padx=10, pady=10)

        # right-hand controls are packed first so long text never pushes them off
        right = tk.Frame(card, bg=bg)
        right.pack(side="right", padx=12)
        Toggle(right, m.enabled, lambda on, mod=m: self.toggle(mod, on), bg=bg).pack(side="right", padx=(10, 0))
        PillButton(right, "View", lambda mod=m: self.select(mod), color=ACCENT, width=64, height=28, bg=bg,
                   font_size=9).pack(side="right")

        mid = tk.Frame(card, bg=bg)
        mid.pack(side="left", fill="both", expand=True, pady=8)
        top = tk.Frame(mid, bg=bg)
        top.pack(anchor="w")
        tk.Label(top, text=m.name, fg=TEXT if m.enabled else DIM, bg=bg, font=(FONT, 12, "bold")).pack(side="left")
        tk.Label(top, text="v" + m.version, fg=GREEN, bg=bg, font=(FONT, 9, "bold")).pack(side="left", padx=8)
        if conflicted:
            tk.Label(top, text="\u26A0 conflict", fg=GOLD, bg=bg, font=(FONT, 9, "bold")).pack(side="left")
        if m.folder == MOD_FOLDER:
            tk.Label(top, text="\u2726 core", fg=ACCENT, bg=bg, font=(FONT, 9, "bold")).pack(side="left")
        desc = m.description or m.folder
        tk.Label(mid, text=desc[:70] + ("..." if len(desc) > 70 else ""), fg=SUB, bg=bg, font=(FONT, 9),
                 anchor="w", justify="left").pack(anchor="w")

        widgets = (card, mid, top, icon)

        def hover(on):
            if self.selected is m:
                return
            c = CARD_HI if on else CARD
            for w in widgets + tuple(top.winfo_children()) + tuple(mid.winfo_children()):
                try:
                    w.configure(bg=c)
                except tk.TclError:
                    pass
            card.configure(highlightbackground=ACCENT if on else BORDER)

        for w in widgets:
            w.bind("<Button-1>", lambda e, mod=m: self.select(mod))
            w.bind("<Double-Button-1>", lambda e, mod=m: self.toggle(mod, not mod.enabled, rerender=True))
        card.bind("<Enter>", lambda e: hover(True))
        card.bind("<Leave>", lambda e: hover(False))

    # ---------------- details
    def select(self, m):
        self.selected = m
        self.render_details()
        self.render_list()

    def render_details(self):
        for w in self.details.winfo_children():
            w.destroy()
        m = self.selected
        if m is None or not os.path.isdir(m.path):
            tk.Label(self.details, text="Select a mod\nto see its details", fg=DIM, bg=PANEL,
                     font=(FONT, 11), pady=60).pack(fill="x")
            return
        thumb = self.img(m.thumb, 96) if m.thumb else None
        (tk.Label(self.details, image=thumb, bg=PANEL) if thumb else letter_tile(self.details, m.name, 96, PANEL)).pack(
            pady=(24, 10))
        tk.Label(self.details, text=m.name, fg=TEXT, bg=PANEL, font=(FONT, 15, "bold"), wraplength=260).pack()
        tk.Label(self.details, text="v" + m.version, fg=GREEN, bg=PANEL, font=(FONT, 10, "bold")).pack()
        tk.Label(self.details, text="ENABLED" if m.enabled else "DISABLED", fg=BG, bg=GREEN if m.enabled else RED,
                 font=(FONT, 8, "bold"), padx=8).pack(pady=8)
        tk.Label(self.details, text=m.description or "No description.", fg=SUB, bg=PANEL, font=(FONT, 9),
                 wraplength=260, justify="left").pack(padx=18, anchor="w")

        files, size = m.stats()
        info = tk.Frame(self.details, bg=CARD)
        info.pack(fill="x", padx=16, pady=14)
        rows = [("Folder", m.folder), ("Files", str(files)), ("Size", human_size(size)), ("Type", ", ".join(m.kind) or "-")]
        if m.workshop_id:
            rows.append(("Workshop", m.workshop_id))
        for k, v in rows:
            r = tk.Frame(info, bg=CARD)
            r.pack(fill="x", padx=10, pady=3)
            tk.Label(r, text=k, fg=DIM, bg=CARD, font=(FONT, 9)).pack(side="left")
            tk.Label(r, text=v, fg=TEXT, bg=CARD, font=(FONT, 9, "bold")).pack(side="right")

        btns = tk.Frame(self.details, bg=PANEL)
        btns.pack(pady=4)
        PillButton(btns, "Disable" if m.enabled else "Enable",
                   lambda: (self.toggle(m, not m.enabled), self.render_details(), self.render_list()),
                   color=RED if m.enabled else GREEN, width=86, height=30).pack(side="left", padx=3)
        PillButton(btns, "Folder", lambda: os.startfile(m.path), color=CARD_HI, fg=TEXT, width=86, height=30).pack(
            side="left", padx=3)
        PillButton(btns, "Uninstall", lambda: self.uninstall(m), color="#5a2238", fg=TEXT, width=86, height=30).pack(
            side="left", padx=3)

    # ---------------- actions
    def refresh(self):
        self.mods = scan_mods(self.game)
        if self.selected:
            self.selected = next((m for m in self.mods if m.folder == self.selected.folder), None)
        write_modlist(self.game, self.mods)
        self.update_count()
        self.game_lbl.configure(text="Game: " + self.game.root)
        if self.page == "installed":
            self.render_list()
        elif self.page in ("profiles", "conflicts"):
            self.show_page(self.page)
        self.render_details()

    def update_count(self):
        on = sum(m.enabled for m in self.mods)
        self.count_lbl.configure(text=f"{on} / {len(self.mods)} mods enabled")

    def toggle(self, m, on, rerender=False):
        try:
            m.set_enabled(on)
        except OSError as e:
            messagebox.showerror("Altar", f"Could not change {m.name}:\n{e}")
        write_modlist(self.game, self.mods)
        self.update_count()
        self.toast(("Enabled " if on else "Disabled ") + m.name, GREEN if on else RED)
        if rerender or self.selected is m:
            self.render_list()
            self.render_details()

    def set_all(self, on):
        for m in self.mods:
            m.set_enabled(on)
        self.refresh()
        self.toast("All mods " + ("enabled" if on else "disabled"))

    def install_zip(self):
        paths = filedialog.askopenfilenames(title="Install mod", filetypes=[("Mod archive", "*.zip")])
        installed = []
        for path in paths:
            try:
                installed.append(self._install_one(path))
            except Exception as e:
                messagebox.showerror("Altar", f"Could not install {os.path.basename(path)}:\n{e}")
        installed = [i for i in installed if i]
        if installed:
            self.refresh()
            self.toast("Installed " + ", ".join(installed))

    def _install_one(self, path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            meta = [n for n in names if n.lower().endswith("metadata.xml") or n.lower().endswith("main.lua")]
            if not meta:
                raise ValueError("No metadata.xml or main.lua in archive - not an Isaac mod.")
            root = os.path.dirname(min(meta, key=lambda n: n.count("/")))
            folder = os.path.basename(root) or os.path.splitext(os.path.basename(path))[0]
            dest = os.path.join(self.game.mods, folder)
            if os.path.exists(dest):
                if not messagebox.askyesno("Altar", f"'{folder}' is already installed. Replace it?"):
                    return None
                shutil.rmtree(dest)
            dest_real = os.path.realpath(dest)
            for n in names:
                if root and not n.startswith(root + "/"):
                    continue
                rel = n[len(root) + 1:] if root else n
                target = os.path.realpath(os.path.join(dest, rel))
                if not target.startswith(dest_real + os.sep):
                    raise ValueError(f"Unsafe path in archive: {n}")
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(n) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
        return folder

    def uninstall(self, m):
        if not messagebox.askyesno("Uninstall", f"Remove '{m.name}'?\n\nIt is moved to {REMOVED_DIR}\n"
                                                f"so you can restore it later."):
            return
        os.makedirs(REMOVED_DIR, exist_ok=True)
        shutil.move(m.path, os.path.join(REMOVED_DIR, f"{m.folder}_{int(time.time())}"))
        self.selected = None
        self.refresh()
        self.toast("Removed " + m.name, RED)

    def launch(self):
        if not os.path.isfile(self.game.exe):
            messagebox.showerror("Altar", f"Game not found:\n{self.game.exe}")
            return
        write_modlist(self.game, self.mods)
        subprocess.Popen([self.game.exe], cwd=self.game.root)
        self.toast("Launching Isaac...", GOLD)

    # ---------------- profiles page
    def page_profiles(self):
        wrap = tk.Frame(self.main, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=14)
        self.page_title(wrap, "Profiles", "Save which mods are enabled and switch between setups in one click.")
        row = tk.Frame(wrap, bg=BG)
        row.pack(fill="x", pady=(0, 10))
        name = tk.StringVar()
        tk.Entry(row, textvariable=name, bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat",
                 font=(FONT, 11)).pack(side="left", fill="x", expand=True, ipady=6)
        PillButton(row, "Save current", lambda: self.save_profile(name.get()), width=120, height=32, bg=BG).pack(
            side="left", padx=8)

        profiles = load_config().get(PROFILES_KEY, {})
        if not profiles:
            tk.Label(wrap, text="No profiles yet.", fg=DIM, bg=BG, font=(FONT, 10)).pack(pady=20)
        for pname, enabled in sorted(profiles.items()):
            c = tk.Frame(wrap, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            c.pack(fill="x", pady=4)
            tk.Label(c, text=pname, fg=TEXT, bg=CARD, font=(FONT, 12, "bold")).pack(side="left", padx=12, pady=10)
            tk.Label(c, text=f"{len(enabled)} mods", fg=SUB, bg=CARD, font=(FONT, 9)).pack(side="left")
            PillButton(c, "Delete", lambda p=pname: self.delete_profile(p), color="#5a2238", fg=TEXT, width=70,
                       height=28, bg=CARD).pack(side="right", padx=8)
            PillButton(c, "Apply", lambda p=pname: self.apply_profile(p), color=GREEN, width=70, height=28,
                       bg=CARD).pack(side="right")

    def _profiles(self, fn):
        cfg = load_config()
        profiles = cfg.setdefault(PROFILES_KEY, {})
        fn(profiles)
        save_config(cfg)

    def save_profile(self, name):
        name = name.strip()
        if not name:
            messagebox.showinfo("Altar", "Type a profile name first.")
            return
        self._profiles(lambda p: p.__setitem__(name, [m.folder for m in self.mods if m.enabled]))
        self.show_page("profiles")
        self.toast("Saved profile " + name)

    def apply_profile(self, name):
        enabled = set(load_config().get(PROFILES_KEY, {}).get(name, []))
        for m in self.mods:
            m.set_enabled(m.folder in enabled)
        self.refresh()
        self.toast(f"Profile '{name}' applied - restart Isaac if it's running", GOLD)

    def delete_profile(self, name):
        self._profiles(lambda p: p.pop(name, None))
        self.show_page("profiles")

    # ---------------- conflicts page
    def page_conflicts(self):
        wrap = ScrollFrame(self.main, BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=14)
        inner = wrap.inner
        self.page_title(inner, "Conflicts", "Files that more than one enabled mod replaces. Only one version wins in game.")
        conflicts = find_conflicts(self.mods)
        if not conflicts:
            tk.Label(inner, text="\u2714  No conflicts between enabled mods.", fg=GREEN, bg=BG,
                     font=(FONT, 12, "bold")).pack(pady=30)
            return
        for f, owners in sorted(conflicts.items())[:300]:
            c = tk.Frame(inner, bg=CARD)
            c.pack(fill="x", pady=2, padx=(0, 8))
            tk.Label(c, text=f, fg=GOLD, bg=CARD, font=("Consolas", 9)).pack(anchor="w", padx=10, pady=(6, 0))
            tk.Label(c, text="  \u2022  ".join(owners), fg=SUB, bg=CARD, font=(FONT, 9)).pack(anchor="w", padx=10,
                                                                                            pady=(0, 6))

    # ---------------- items page
    def page_items(self):
        wrap = ScrollFrame(self.main, BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=14)
        inner = wrap.inner
        self.page_title(inner, "Altar Items", "32 animated custom items. In game press F2 > Items > Altar to spawn "
                                             "them, or F4 and type: give <name>. Combos: F2 > Combos.")
        grid = tk.Frame(inner, bg=BG)
        grid.pack(anchor="w")
        names = sorted(f for f in os.listdir(ASSETS) if f.startswith("item_")) if os.path.isdir(ASSETS) else []
        for i, f in enumerate(names):
            im = self.img(os.path.join(ASSETS, f), 56)
            cell = tk.Frame(grid, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            cell.grid(row=i // 8, column=i % 8, padx=4, pady=4)
            if im:
                tk.Label(cell, image=im, bg=CARD).pack(padx=6, pady=(6, 0))
            label = f[5:-4].replace("_", " ").title()
            tk.Label(cell, text=label, fg=SUB, bg=CARD, font=(FONT, 8), width=13).pack(pady=(0, 6))

        tk.Label(inner, text="Hotkeys", fg=TEXT, bg=BG, font=(FONT, 13, "bold")).pack(anchor="w", pady=(16, 4))
        for line in ("F2  -  open the Altar menu (or click the gem button)",
                     "F3  -  live stat overlay",
                     "F4  -  command console  (try: boss monstro, combo all, tp devil, give overclock 3)",
                     "~   -  game console also works: altar <command>"):
            tk.Label(inner, text=line, fg=SUB, bg=BG, font=(FONT, 10)).pack(anchor="w")

    # ---------------- settings page
    def page_settings(self):
        wrap = tk.Frame(self.main, bg=BG)
        wrap.pack(fill="both", expand=True, padx=16, pady=14)
        self.page_title(wrap, "Settings", "Where Altar looks for The Binding of Isaac.")
        card = tk.Frame(wrap, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")
        tk.Label(card, text="Game folder", fg=DIM, bg=CARD, font=(FONT, 9)).pack(anchor="w", padx=12, pady=(10, 0))
        tk.Label(card, text=self.game.root, fg=TEXT, bg=CARD, font=(FONT, 10, "bold"), wraplength=560,
                 justify="left").pack(anchor="w", padx=12, pady=(0, 10))
        row = tk.Frame(card, bg=CARD)
        row.pack(anchor="w", padx=12, pady=(0, 12))
        PillButton(row, "Change...", self.change_game, width=110, height=30, bg=CARD).pack(side="left")
        PillButton(row, "Open game folder", lambda: os.startfile(self.game.root), color=CARD_HI, fg=TEXT, width=140,
                   height=30, bg=CARD).pack(side="left", padx=8)
        PillButton(row, "Open Altar data", lambda: (os.makedirs(CONFIG_DIR, exist_ok=True), os.startfile(CONFIG_DIR)),
                   color=CARD_HI, fg=TEXT, width=140, height=30, bg=CARD).pack(side="left")

        link = tk.Frame(wrap, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        link.pack(fill="x", pady=(10, 0))
        txt = tk.Frame(link, bg=CARD)
        txt.pack(side="left", padx=12, pady=8)
        tk.Label(txt, text="Clipboard link", fg=TEXT, bg=CARD, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(txt, text="While this app is open, anything you copy can be pasted into the in-game "
                           "console with Ctrl+V", fg=SUB, bg=CARD, font=(FONT, 9)).pack(anchor="w")

        def set_link(on):
            self.clip_link = on
            cfg = load_config()
            cfg["clipboard_link"] = on
            save_config(cfg)
        Toggle(link, self.clip_link, set_link).pack(side="right", padx=12)

        upd = tk.Frame(wrap, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
        upd.pack(fill="x", pady=(10, 0))
        txt = tk.Frame(upd, bg=CARD)
        txt.pack(side="left", padx=12, pady=8)
        tk.Label(txt, text="Auto-update", fg=TEXT, bg=CARD, font=(FONT, 10, "bold")).pack(anchor="w")
        tk.Label(txt, text=f"Check GitHub for new Altar releases when the app starts (you have v{VERSION})",
                 fg=SUB, bg=CARD, font=(FONT, 9)).pack(anchor="w")

        def set_auto(on):
            cfg = load_config()
            cfg["auto_update"] = on
            save_config(cfg)
        Toggle(upd, load_config().get("auto_update", True), set_auto).pack(side="right", padx=12)
        PillButton(upd, "Check now", lambda: self.check_for_update(manual=True), color=CARD_HI, fg=TEXT, width=100,
                   height=28, bg=CARD).pack(side="right")

        others = [d for d in find_game_dirs() if os.path.normcase(d) != os.path.normcase(self.game.root)]
        if others:
            tk.Label(wrap, text="Other Isaac installs found", fg=TEXT, bg=BG, font=(FONT, 12, "bold")).pack(
                anchor="w", pady=(16, 4))
            for d in others:
                r = tk.Frame(wrap, bg=CARD)
                r.pack(fill="x", pady=2)
                tk.Label(r, text=d, fg=SUB, bg=CARD, font=(FONT, 9)).pack(side="left", padx=10, pady=8)
                PillButton(r, "Use this", lambda p=d: self.set_game(p), color=GREEN, width=80, height=26,
                           bg=CARD).pack(side="right", padx=8)
        tk.Label(wrap, text=f"Altar v{VERSION}", fg=DIM, bg=BG, font=(FONT, 9)).pack(anchor="w", pady=(20, 0))

    def change_game(self):
        path = filedialog.askdirectory(title="Select your Isaac folder (contains isaac-ng.exe)")
        if path:
            if is_game_dir(path):
                self.set_game(path)
            else:
                messagebox.showerror("Altar", "That folder has no isaac-ng.exe.")

    def set_game(self, path):
        cfg = load_config()
        cfg["game_dir"] = os.path.normpath(path)
        save_config(cfg)
        self.game = Game(cfg["game_dir"])
        self.selected = None
        self.refresh()
        self.show_page("settings")
        self.toast("Game folder updated")


def main():
    args = sys.argv[1:]
    game_arg = args[args.index("--game") + 1] if "--game" in args else None
    game_dir = resolve_game(game_arg)
    if not game_dir:
        return
    if "--sync" in args:  # headless: just regenerate the in-game mod list
        game = Game(game_dir)
        write_modlist(game, scan_mods(game))
        return
    cfg = load_config()
    if cfg.get("game_dir") != game_dir:
        cfg["game_dir"] = game_dir
        save_config(cfg)
    App(game_dir).mainloop()


if __name__ == "__main__":
    main()
