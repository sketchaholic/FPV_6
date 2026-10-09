# Lap Callout

Type in an FPV lap time and hear it read out like a race timer, then save it as a `.wav` file you can drop into your video edits (DaVinci Resolve, Premiere, etc.).

![Lap Callout app](docs/screenshot.png)

> *"Vi, lap 3, 23.45, total, 1 minute, 10.35"*

Lap timers like RotorHazard and FPVTrackside read lap times with your computer's built-in text-to-speech voice. Lap Callout uses those same voices (Microsoft David / Zira on Windows), so your edited flight videos sound like a real race.

## Features

- Reads lap times out loud using your computer's built-in voices
- Saves each callout as a `.wav` audio file
- Optional pilot name and lap number, with auto-increment
- Optional running **total time** across laps
- Saves to your **Downloads** folder by default, or a folder you choose
- Voice picker and speed slider
- Never overwrites files: duplicates are saved as `name (2).wav`
- No extra installs: just Python

## Requirements

- **Windows 10/11** or **macOS**
- **Python 3.8+** from [python.org](https://www.python.org/downloads/)
  - On Windows, tick **"Add python.exe to PATH"** during install

No `pip install` needed. It uses Tkinter (included with Python) and the speech engine built into your OS.

## Getting started

1. Download this repo (**Code → Download ZIP**) and unzip it, or clone it:
   ```
   git clone https://github.com/FPV_6/LapCallout.git
   ```
2. Start the app:
   - **Windows:** double-click `Lap Callout.bat`
   - **Any OS:** run `python lap_callout.py`

> The first time you run the `.bat`, Windows may show *"Windows protected your PC"*. Click **More info → Run anyway**.

## How to use

| Field | What it does |
|---|---|
| **Pilot** | Optional name read at the start of the callout |
| **Lap #** | Optional lap number. Tick **auto +1** to move to the next lap after each save |
| **Lap time** | Type `23.45`, `1:03.2` or `83.2` (seconds over 60 are converted to minutes) |
| **Total time** | Tick **Read total** to add the running total to the callout. **Reset** starts a new flight |
| **Voice / Speed** | Choose any installed voice and how fast it talks |
| **Save to** | Folder for quick saves (Downloads by default). Click **Change...** to pick another |

The line under the fields shows exactly what will be spoken before you press anything.

### Buttons and shortcuts

| Button | Shortcut | Action |
|---|---|---|
| **Speak** | `Enter` | Read the callout out loud |
| **Save .wav** | `Ctrl+S` | Save straight into the *Save to* folder |
| **Save As...** | | Choose the folder and file name for this one file |
| **Next lap** | | Add the lap to the total without saving audio |

Saved files are named like `Vi_lap3_23-45.wav` so they sort nicely in your editor's media pool.

### Typical workflow

1. Enter your pilot name and set **Lap #** to 1.
2. Type the first lap time and press `Enter` to preview it.
3. Press `Ctrl+S` to save it. The lap number goes up and the box clears.
4. Repeat for each lap. Tick **Read total** if you want the running total called out.
5. Drag the `.wav` files from your Downloads folder into your video editor.

## Voices

- **Windows:** Microsoft David (male) is chosen by default if installed, otherwise Zira (female). Add more under **Settings → Time & language → Speech**.
- **macOS:** English voices from **System Settings → Accessibility → Spoken Content**.

## Files

| File | Purpose |
|---|---|
| `lap_callout.py` | The app |
| `Lap Callout.bat` | Windows launcher, so there's no console window or typing. Keep it in the same folder as `lap_callout.py` |
| `docs/screenshot.png` | Screenshot used in this README |

## Troubleshooting

- **"Could not find Python"** when running the `.bat`: reinstall Python and tick **Add python.exe to PATH**.
- **No voices listed:** the system default voice is used. Check your OS speech settings.
- **Linux:** not supported yet.
