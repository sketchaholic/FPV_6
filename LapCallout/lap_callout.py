"""
Lap Callout - type a lap time, hear it read out like an FPV race timer,
and save it as a .wav for your edits.

No pip installs needed:
  - Windows: uses the built-in Windows voices (Microsoft David / Zira) via PowerShell
  - macOS:   uses the built-in `say` command

Run:  python lap_callout.py   (or use "Lap Callout.bat" on Windows)
"""
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
NO_WINDOW = 0x08000000 if IS_WIN else 0  # CREATE_NO_WINDOW


# ---------------------------------------------------------------- folders
def downloads_folder():
    """The user's real Downloads folder (handles a moved/redirected one on Windows)."""
    if IS_WIN:
        try:
            import ctypes
            from ctypes import wintypes
            from uuid import UUID

            class GUID(ctypes.Structure):
                _fields_ = [("d1", wintypes.DWORD), ("d2", wintypes.WORD),
                            ("d3", wintypes.WORD), ("d4", ctypes.c_ubyte * 8)]

            u = UUID("374DE290-123F-4565-9164-39C4925E467B")  # FOLDERID_Downloads
            g = GUID(u.fields[0], u.fields[1], u.fields[2],
                     (ctypes.c_ubyte * 8)(*u.bytes[8:]))
            p = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None,
                                                          ctypes.byref(p)) == 0:
                path = p.value
                ctypes.windll.ole32.CoTaskMemFree(p)
                if path and os.path.isdir(path):
                    return path
        except Exception:
            pass
    path = os.path.join(os.path.expanduser("~"), "Downloads")
    return path if os.path.isdir(path) else os.path.expanduser("~")


def unique_path(folder, filename):
    """Avoid overwriting: name.wav -> name (2).wav -> name (3).wav ..."""
    base, ext = os.path.splitext(filename)
    path, n = os.path.join(folder, filename), 2
    while os.path.exists(path):
        path = os.path.join(folder, f"{base} ({n}){ext}")
        n += 1
    return path


# ---------------------------------------------------------------- speech backend
PS_COMMON = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
)


def _powershell(script, env_extra=None):
    env = dict(os.environ, **(env_extra or {}))
    return subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True, text=True, env=env, creationflags=NO_WINDOW,
    )


def list_voices():
    if IS_WIN:
        r = _powershell(PS_COMMON +
                        "$s.GetInstalledVoices() | Where-Object Enabled | "
                        "ForEach-Object { $_.VoiceInfo.Name }")
        return [v.strip() for v in r.stdout.splitlines() if v.strip()]
    if IS_MAC:
        r = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
        voices = []
        for line in r.stdout.splitlines():
            m = re.match(r"^(.*?)\s+([a-z]{2,3}[_-][A-Za-z0-9]+)\s+#", line)
            if m and m.group(2).lower().startswith("en"):
                voices.append(m.group(1).strip())
        return voices
    return []


def speak(text, voice, rate, wav_path=None):
    """rate: -5 (slow) .. +5 (fast). Blocks until done. Returns error text or ''."""
    if IS_WIN:
        # Text/voice/path go through env vars so nothing needs escaping.
        script = PS_COMMON + (
            "if ($env:LC_VOICE) { $s.SelectVoice($env:LC_VOICE) };"
            "$s.Rate = [int]$env:LC_RATE;"
            "if ($env:LC_OUT) { $s.SetOutputToWaveFile($env:LC_OUT) };"
            "$s.Speak($env:LC_TEXT); $s.Dispose()"
        )
        r = _powershell(script, {
            "LC_TEXT": text, "LC_VOICE": voice or "",
            "LC_RATE": str(int(rate) * 2), "LC_OUT": wav_path or "",
        })
        return r.stderr.strip()
    if IS_MAC:
        cmd = ["say", "-r", str(175 + int(rate) * 25)]
        if voice:
            cmd += ["-v", voice]
        if wav_path:
            cmd += ["--file-format=WAVE", "--data-format=LEI16@44100", "-o", wav_path]
        r = subprocess.run(cmd + [text], capture_output=True, text=True)
        return r.stderr.strip()
    return "Only Windows and macOS are supported."


# ---------------------------------------------------------------- lap time text
TIME_RE = re.compile(r"^\s*(?:(\d+)\s*:\s*)?(\d+(?:\.\d+)?)\s*$")


def parse_time(raw):
    """'23.45' -> (23.45, 2); '1:03.5' -> (63.5, 1). Returns (seconds, decimals) or None."""
    m = TIME_RE.match(raw.replace(",", "."))
    if not m:
        return None
    secs = float(m.group(2))
    if m.group(1) and secs >= 60:
        return None
    decimals = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
    return int(m.group(1) or 0) * 60 + secs, decimals


def spoken_time(seconds, decimals):
    """63.5 -> '1 minute, 3.5'   23.45 -> '23.45'"""
    seconds = round(seconds, decimals)
    minutes = int(seconds // 60)
    sec_txt = f"{seconds - minutes * 60:.{decimals}f}"
    if minutes:
        min_txt = f"{minutes} minute{'s' if minutes > 1 else ''}"
        return min_txt if float(sec_txt) == 0 else f"{min_txt}, {sec_txt}"
    return sec_txt


def short_time(seconds, decimals):
    """63.5 -> '1:03.5'  (for on-screen display)"""
    seconds = round(seconds, decimals)
    minutes = int(seconds // 60)
    width = 3 + decimals if decimals else 2
    secs = f"{seconds - minutes * 60:0{width}.{decimals}f}"
    return f"{minutes}:{secs}" if minutes else f"{seconds:.{decimals}f}"


def build_phrase(pilot, lap, raw_time, total=None):
    """total: optional (seconds, decimals) to append as 'total, ...'."""
    t = parse_time(raw_time)
    if t is None:
        return None
    parts = []
    if pilot.strip():
        parts.append(pilot.strip())
    if lap.strip():
        parts.append(f"lap {lap.strip()}")
    parts.append(spoken_time(*t))
    if total:
        parts.append(f"total, {spoken_time(*total)}")
    return ", ".join(parts)


def default_filename(pilot, lap, raw_time, with_total=False):
    t = raw_time.strip().replace(":", "m").replace(".", "-")
    bits = [re.sub(r"\W+", "", pilot)] if pilot.strip() else []
    if lap.strip():
        bits.append(f"lap{lap.strip()}")
    bits.append(t)
    if with_total:
        bits.append("total")
    return "_".join(bits) + ".wav"


# ---------------------------------------------------------------- UI
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Lap Callout")
        self.resizable(False, False)
        pad = {"padx": 8, "pady": 4}

        # running total of laps already committed (saved or "Next lap")
        self.total_secs = 0.0
        self.total_dec = 0
        self.total_laps = 0

        frm = ttk.Frame(self, padding=12)
        frm.grid()

        self.pilot = tk.StringVar()
        self.lap = tk.StringVar(value="1")
        self.time = tk.StringVar()
        self.voice = tk.StringVar()
        self.rate = tk.IntVar(value=0)
        self.auto_inc = tk.BooleanVar(value=True)
        self.read_total = tk.BooleanVar(value=False)
        self.save_dir = tk.StringVar(value=downloads_folder())
        self.status = tk.StringVar(value="Type a lap time like 23.45 or 1:03.2")

        r = 0
        ttk.Label(frm, text="Pilot (optional)").grid(row=r, column=0, sticky="w", **pad)
        ttk.Entry(frm, textvariable=self.pilot, width=22).grid(row=r, column=1, sticky="we", **pad)

        r += 1
        ttk.Label(frm, text="Lap # (optional)").grid(row=r, column=0, sticky="w", **pad)
        lapbox = ttk.Frame(frm)
        lapbox.grid(row=r, column=1, sticky="w", **pad)
        ttk.Spinbox(lapbox, from_=0, to=999, textvariable=self.lap, width=6).pack(side="left")
        ttk.Checkbutton(lapbox, text="auto +1", variable=self.auto_inc).pack(side="left", padx=8)

        r += 1
        ttk.Label(frm, text="Lap time").grid(row=r, column=0, sticky="w", **pad)
        e = ttk.Entry(frm, textvariable=self.time, width=22, font=("Segoe UI", 16))
        e.grid(row=r, column=1, sticky="we", **pad)
        e.focus_set()

        r += 1
        ttk.Label(frm, text="Total time").grid(row=r, column=0, sticky="w", **pad)
        totbox = ttk.Frame(frm)
        totbox.grid(row=r, column=1, sticky="we", **pad)
        ttk.Checkbutton(totbox, text="Read total", variable=self.read_total,
                        command=self.update_preview).pack(side="left")
        self.total_lbl = ttk.Label(totbox, text="", foreground="#555")
        self.total_lbl.pack(side="left", padx=8)
        ttk.Button(totbox, text="Reset", width=6, command=self.reset_total).pack(side="right")

        r += 1
        ttk.Label(frm, text="Voice").grid(row=r, column=0, sticky="w", **pad)
        self.voice_box = ttk.Combobox(frm, textvariable=self.voice, state="readonly", width=30)
        self.voice_box.grid(row=r, column=1, sticky="we", **pad)

        r += 1
        ttk.Label(frm, text="Speed").grid(row=r, column=0, sticky="w", **pad)
        ttk.Scale(frm, from_=-5, to=5, variable=self.rate,
                  command=lambda v: self.rate.set(round(float(v)))).grid(row=r, column=1, sticky="we", **pad)

        r += 1
        ttk.Label(frm, text="Save to").grid(row=r, column=0, sticky="w", **pad)
        dirbox = ttk.Frame(frm)
        dirbox.grid(row=r, column=1, sticky="we", **pad)
        self.dir_lbl = ttk.Label(dirbox, text="", width=26, foreground="#555")
        self.dir_lbl.pack(side="left")
        ttk.Button(dirbox, text="Change...", command=self.choose_folder).pack(side="right")

        r += 1
        self.preview = ttk.Label(frm, text="", foreground="#555", wraplength=380)
        self.preview.grid(row=r, column=0, columnspan=2, sticky="w", **pad)

        r += 1
        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=2, pady=(8, 4))
        self.speak_btn = ttk.Button(btns, text="Speak (Enter)", command=self.on_speak)
        self.speak_btn.pack(side="left", padx=3)
        self.save_btn = ttk.Button(btns, text="Save .wav (Ctrl+S)", command=self.on_save)
        self.save_btn.pack(side="left", padx=3)
        self.saveas_btn = ttk.Button(btns, text="Save As...", command=self.on_save_as)
        self.saveas_btn.pack(side="left", padx=3)
        ttk.Button(btns, text="Next lap", command=self.on_next).pack(side="left", padx=3)

        r += 1
        ttk.Label(frm, textvariable=self.status, foreground="#336", wraplength=380).grid(
            row=r, column=0, columnspan=2, sticky="w", **pad)

        for v in (self.pilot, self.lap, self.time):
            v.trace_add("write", lambda *_: self.update_preview())
        self.save_dir.trace_add("write", lambda *_: self.update_dir_label())
        self.bind("<Return>", lambda _e: self.on_speak())
        self.bind("<Control-s>", lambda _e: self.on_save())
        self.bind("<Command-s>", lambda _e: self.on_save())

        self.update_dir_label()
        self.update_preview()
        threading.Thread(target=self.load_voices, daemon=True).start()

    # -- helpers
    def load_voices(self):
        voices = list_voices()

        def apply():
            self.voice_box["values"] = voices
            pref = next((v for v in voices if "David" in v), None) or \
                next((v for v in voices if "Zira" in v), None) or \
                (voices[0] if voices else "")
            self.voice.set(pref)
            if not voices:
                self.status.set("No voices found - the system default voice will be used.")
        self.after(0, apply)

    def update_dir_label(self):
        path = self.save_dir.get()
        shown = path if len(path) <= 34 else "..." + path[-31:]
        self.dir_lbl.config(text=shown)

    def total_with_current(self):
        """Running total including the lap currently typed in (if valid)."""
        t = parse_time(self.time.get())
        secs, dec = self.total_secs, self.total_dec
        if t:
            secs += t[0]
            dec = max(dec, t[1])
        return secs, dec

    def update_preview(self):
        total = self.total_with_current()
        laps = self.total_laps + (1 if parse_time(self.time.get()) else 0)
        self.total_lbl.config(
            text=f"{short_time(*total)}  ({laps} lap{'s' if laps != 1 else ''})" if laps else "")
        phrase = self.make_phrase()
        self.preview.config(text=f'Will say: "{phrase}"' if phrase else "")

    def make_phrase(self):
        total = self.total_with_current() if self.read_total.get() else None
        return build_phrase(self.pilot.get(), self.lap.get(), self.time.get(), total)

    def current_phrase(self):
        phrase = self.make_phrase()
        if not phrase:
            self.status.set("That doesn't look like a lap time. Try 23.45 or 1:03.2")
        return phrase

    def run_bg(self, fn, done_msg):
        for b in (self.speak_btn, self.save_btn, self.saveas_btn):
            b.state(["disabled"])

        def work():
            err = fn()

            def finish():
                for b in (self.speak_btn, self.save_btn, self.saveas_btn):
                    b.state(["!disabled"])
                self.status.set(f"Error: {err}" if err else done_msg)
            self.after(0, finish)
        threading.Thread(target=work, daemon=True).start()

    def commit_lap(self):
        """Add the typed lap to the running total, bump lap #, clear the box."""
        t = parse_time(self.time.get())
        if t:
            self.total_secs += t[0]
            self.total_dec = max(self.total_dec, t[1])
            self.total_laps += 1
        if self.auto_inc.get() and self.lap.get().strip().isdigit():
            self.lap.set(str(int(self.lap.get()) + 1))
        self.time.set("")
        self.update_preview()

    def reset_total(self):
        self.total_secs, self.total_dec, self.total_laps = 0.0, 0, 0
        if self.auto_inc.get():
            self.lap.set("1")
        self.update_preview()
        self.status.set("Total reset.")

    def save_to(self, path, phrase):
        self.status.set("Saving...")
        self.run_bg(lambda: speak(phrase, self.voice.get(), self.rate.get(), path),
                    f"Saved {os.path.basename(path)}  ->  {os.path.dirname(path)}")
        self.commit_lap()

    def suggested_name(self):
        return default_filename(self.pilot.get(), self.lap.get(), self.time.get(),
                                self.read_total.get())

    # -- actions
    def on_speak(self):
        phrase = self.current_phrase()
        if not phrase:
            return
        self.status.set("Speaking...")
        self.run_bg(lambda: speak(phrase, self.voice.get(), self.rate.get()),
                    "Done. Ctrl+S to save it as a .wav")

    def on_save(self):
        """Save straight into the 'Save to' folder (Downloads by default)."""
        phrase = self.current_phrase()
        if not phrase:
            return
        folder = self.save_dir.get()
        if not os.path.isdir(folder):
            folder = downloads_folder()
            self.save_dir.set(folder)
        self.save_to(unique_path(folder, self.suggested_name()), phrase)

    def on_save_as(self):
        """Pick any folder / file name for this one file."""
        phrase = self.current_phrase()
        if not phrase:
            return
        path = filedialog.asksaveasfilename(
            title="Save callout", defaultextension=".wav",
            initialdir=self.save_dir.get(), initialfile=self.suggested_name(),
            filetypes=[("WAV audio", "*.wav")])
        if path:
            self.save_to(path, phrase)

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose where to save callouts",
                                         initialdir=self.save_dir.get())
        if folder:
            self.save_dir.set(os.path.normpath(folder))
            self.status.set("Ctrl+S will now save here.")

    def on_next(self):
        if not parse_time(self.time.get()):
            self.status.set("Type a lap time first.")
            return
        self.commit_lap()
        self.status.set("Lap added to total.")


if __name__ == "__main__":
    if not (IS_WIN or IS_MAC):
        messagebox.showerror("Lap Callout", "This app needs Windows or macOS.")
        sys.exit(1)
    App().mainloop()
