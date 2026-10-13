# Gesture Volume Control

I wanted to change my laptop volume without touching the keyboard, so I built this. It uses your webcam to track your hand, and you control volume just by pinching your fingers. No extra hardware needed.

Pinch your thumb and index finger close together and the volume goes down. Spread them apart and it goes up. I also added brightness control, mute, lock and play/pause because it was fun to build.

**Built with:** Python, OpenCV, MediaPipe, PyAutoGUI

## How it works

MediaPipe finds 21 points on your hand in every frame. OpenCV measures the distance between your thumb tip and index fingertip. That distance gets divided by the size of your palm (so it works whether you sit close or far from the camera) and then mapped to a number from 0 to 100. That number becomes your volume.

Nothing is recorded or sent anywhere. The webcam feed is only processed live on your own machine.

## What you can do

| Gesture | What happens |
| --- | --- |
| Pinch with your right hand (keep the other three fingers up) | Controls volume |
| Pinch with your left hand | Controls brightness |
| Make a fist and hold for 1 second | Mute / unmute |
| Peace sign, hold for 1 second | Lock / unlock (so it stops reacting) |
| Index and pinky up, hold for 1 second | Play / pause |

Keep your hand upright with your palm facing the camera, otherwise the finger detection gets confused.

Keyboard shortcuts (click the camera window first):

| Key | What it does |
| --- | --- |
| H | show / hide the help text |
| L | lock / unlock |
| M | mute / unmute |
| B | brightness on / off |
| S | snap volume to steps of 5 |
| N | save current pinch as the minimum |
| X | save current pinch as the maximum |
| R | reset the min / max |
| P | save a screenshot |
| Q | quit |

## Setup from scratch (Windows + VS Code)

If you've never set any of this up before, just follow these in order.

### 1. Install Python

1. Go to python.org/downloads and download Python **3.12** (3.9 to 3.12 all work). Newer versions might not work with MediaPipe.
2. Run the installer and **tick "Add python.exe to PATH"** on the first screen. People forget this and then nothing works.
3. Open a terminal and run `python --version` to check it installed.

### 2. Install VS Code

1. Download it from code.visualstudio.com and install it.
2. Open VS Code, click the Extensions icon on the left (the four squares), search for **Python** (the one by Microsoft) and install it.

### 3. Get the project

Either download the ZIP from this page (green Code button, then Download ZIP) and unzip it, or clone it:

```
git clone https://github.com/SHARIYAR2201/Gesture_Volume_Control.git
cd Gesture_Volume_Control
```

In VS Code go to **File > Open Folder** and open the project folder.

### 4. Make a virtual environment

Open the terminal inside VS Code with `` Ctrl + ` `` and run:

```
python -m venv venv
venv\Scripts\activate
```

You should now see `(venv)` at the start of the line.

If PowerShell says running scripts is disabled, run this once and try again:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 5. Install the packages

```
pip install -r requirements.txt
```

This takes a minute or two. The MediaPipe version is pinned on purpose, because newer versions removed the part this project uses and you'll get an error saying `mediapipe has no attribute 'solutions'`.

### 6. Pick the right interpreter

Press `Ctrl + Shift + P`, type **Python: Select Interpreter**, and choose the one inside the `venv` folder. The bottom right corner of VS Code should show `venv`.

### 7. Run it

Open `gesture_control.py` and press the play button at the top right, or type this in the terminal:

```
python gesture_control.py
```

Windows might ask for camera permission the first time. Allow it. A window with your webcam feed should pop up. Hold your hand up and try pinching.

To stop it, click on the camera window and press **Q**, or click in the terminal and press `Ctrl + C`.

## Calibration

Everyone's hands and cameras are a bit different. If the volume reaches 100 too early or never gets to 0, do this:

1. Pinch your fingers fully closed and hold it, then press **N**.
2. Open your fingers as wide as is comfortable and hold it, then press **X**.

Your values are saved in a `config.json` file next to the script (it's ignored by git, so it stays on your machine). Press **R** if you want to go back to the defaults.

## Other systems

- **Windows:** gives you exact volume control through `pycaw`. This is what I built and tested it on.
- **macOS / Linux:** the script uses `osascript` or `pactl` for volume. I haven't tested these much, so no promises. You can skip `pycaw` and `comtypes` there. Activate the venv with `source venv/bin/activate`.
- If volume can't be set directly, it falls back to pressing the volume keys, which only estimates the level and can drift a bit.

## Problems I ran into

- **`mediapipe has no attribute 'solutions'`**: you have a newer MediaPipe. Run `pip install mediapipe==0.10.21`.
- **Black window or no camera**: close anything else using the webcam (Zoom, Teams, browser tabs). If you have more than one camera, change `cv2.VideoCapture(0)` to `1` in the script.
- **Gestures not detected**: check your lighting, keep your hand upright, and keep it fully in the frame.
- **Brightness doesn't work**: some monitors don't support software brightness control. Press **B** to turn it off.
- **Pip install fails**: check you're on Python 3.9 to 3.12 and that `(venv)` is showing in the terminal.

## Notes

If you take screenshots with **P** they'll show your face, so check before you upload any to GitHub. They're ignored by git by default too.

Feel free to fork it and change the gestures. Pull requests are welcome.
