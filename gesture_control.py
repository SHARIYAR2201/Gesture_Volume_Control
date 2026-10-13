import json
import math
import os
import platform
import re
import shutil
import subprocess
import time

import cv2
import mediapipe as mp
import pyautogui

try:
    import screen_brightness_control as sbc
    HAS_BRIGHTNESS = True
except Exception:
    HAS_BRIGHTNESS = False

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

CONFIG_FILE = "config.json"
DEFAULTS = {
    "min_ratio": 0.15,
    "max_ratio": 1.0,
    "snap": False,
    "brightness": True,
    "show_help": True,
}

HELP = [
    "Pinch: right hand volume, left hand brightness",
    "Fist: mute | Peace: lock | Rock: play/pause (hold 1s)",
    "H help | L lock | M mute | B brightness | S snap",
    "N min | X max | R reset | P screenshot | Q quit",
]


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


class Volume:
    def __init__(self):
        self.system = platform.system()
        self.mode = "keys"
        self.muted = False
        self.level = 50
        self.endpoint = None

        if self.system == "Windows":
            try:
                from ctypes import POINTER, cast
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                device = AudioUtilities.GetSpeakers()
                if hasattr(device, "EndpointVolume"):
                    self.endpoint = device.EndpointVolume
                else:
                    iface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    self.endpoint = cast(iface, POINTER(IAudioEndpointVolume))
                self.mode = "pycaw"
                self.muted = bool(self.endpoint.GetMute())
            except Exception:
                self.mode = "keys"
        elif self.system == "Darwin":
            self.mode = "osascript"
        elif self.system == "Linux" and shutil.which("pactl"):
            self.mode = "pactl"

        if self.mode == "keys":
            for _ in range(50):
                pyautogui.press("volumedown")
            for _ in range(25):
                pyautogui.press("volumeup")
        else:
            self.read()

    def run(self, *cmd):
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=2).stdout
        except Exception:
            return ""

    def read(self):
        try:
            if self.mode == "pycaw":
                self.level = round(self.endpoint.GetMasterVolumeLevelScalar() * 100)
                self.muted = bool(self.endpoint.GetMute())
            elif self.mode == "osascript":
                out = self.run("osascript", "-e", "output volume of (get volume settings)")
                self.level = int(out.strip())
            elif self.mode == "pactl":
                out = self.run("pactl", "get-sink-volume", "@DEFAULT_SINK@")
                found = re.search(r"(\d+)%", out)
                if found:
                    self.level = int(found.group(1))
        except Exception:
            pass

    def set(self, value):
        value = max(0, min(100, int(value)))
        if value == self.level:
            return
        if self.mode == "pycaw":
            self.endpoint.SetMasterVolumeLevelScalar(value / 100, None)
        elif self.mode == "osascript":
            self.run("osascript", "-e", f"set volume output volume {value}")
        elif self.mode == "pactl":
            self.run("pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{value}%")
        else:
            diff = value - self.level
            presses = abs(diff) // 2
            if presses == 0:
                return
            pyautogui.press("volumeup" if diff > 0 else "volumedown", presses=presses)
            value = self.level + (2 * presses if diff > 0 else -2 * presses)
        self.level = value

    def toggle_mute(self):
        self.muted = not self.muted
        if self.mode == "pycaw":
            self.endpoint.SetMute(int(self.muted), None)
        elif self.mode == "osascript":
            self.run("osascript", "-e", f"set volume output muted {str(self.muted).lower()}")
        elif self.mode == "pactl":
            self.run("pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle")
        else:
            pyautogui.press("volumemute")


def fingers_up(lm):
    tips = (8, 12, 16, 20)
    pips = (6, 10, 14, 18)
    return [1 if lm[t].y < lm[p].y else 0 for t, p in zip(tips, pips)]


def classify(lm):
    up = fingers_up(lm)
    if up == [0, 0, 0, 0]:
        return "fist"
    if up == [1, 1, 0, 0]:
        return "peace"
    if up == [1, 0, 0, 1]:
        return "rock"
    if up[1] and up[2] and up[3]:
        return "pinch"
    return None


class Hold:
    def __init__(self, seconds=1.0):
        self.seconds = seconds
        self.name = None
        self.start = 0
        self.armed = True

    def update(self, name):
        now = time.time()
        if name != self.name:
            self.name = name
            self.start = now
            self.armed = True
        if name is None or not self.armed:
            return False, 0.0
        progress = min(1.0, (now - self.start) / self.seconds)
        if progress >= 1.0:
            self.armed = False
            return True, 1.0
        return False, progress


def text(img, msg, pos, scale=0.6, color=(255, 255, 255), thick=2):
    cv2.putText(img, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2)
    cv2.putText(img, msg, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick)


def bar(img, x, label, value, color):
    top, bottom = 120, 420
    fill = int((bottom - top) * value / 100)
    cv2.rectangle(img, (x, top), (x + 30, bottom), (255, 255, 255), 2)
    cv2.rectangle(img, (x, bottom - fill), (x + 30, bottom), color, -1)
    text(img, f"{int(value)}%", (x - 8, bottom + 28), 0.6, color)
    text(img, label, (x - 8, top - 12), 0.5)


def main():
    cfg = load_config()
    vol = Volume()
    use_brightness = HAS_BRIGHTNESS and cfg["brightness"]
    try:
        bright = sbc.get_brightness()[0] if HAS_BRIGHTNESS else 50
    except Exception:
        bright = 50
        use_brightness = False

    hands = mp.solutions.hands.Hands(
        max_num_hands=2, min_detection_confidence=0.7, min_tracking_confidence=0.7
    )
    draw = mp.solutions.drawing_utils
    connections = mp.solutions.hands.HAND_CONNECTIONS

    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    hold = Hold()
    locked = False
    smooth_v = float(vol.level)
    smooth_b = float(bright)
    last_ratio = 0.0
    last_read = 0.0
    last_bright_set = 0.0
    prev_time = 0.0
    message = ""
    message_until = 0.0

    def notify(msg):
        nonlocal message, message_until
        message = msg
        message_until = time.time() + 1.5

    def toggle_mute():
        vol.toggle_mute()
        notify("MUTED" if vol.muted else "UNMUTED")

    def toggle_lock():
        nonlocal locked
        locked = not locked
        notify("LOCKED" if locked else "UNLOCKED")

    while cap.isOpened():
        ok, frame = cap.read()
        if not ok:
            break
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        now = time.time()
        result = hands.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if now - last_read > 1.0:
            vol.read()
            last_read = now

        gesture = None
        pinch_volume = False
        pinch_brightness = False
        target_v = smooth_v
        target_b = smooth_b

        if result.multi_hand_landmarks:
            for hand, info in zip(result.multi_hand_landmarks, result.multi_handedness):
                side = info.classification[0].label
                lm = hand.landmark
                draw.draw_landmarks(frame, hand, connections)
                g = classify(lm)

                if g in ("fist", "peace", "rock"):
                    gesture = g
                    wx, wy = int(lm[0].x * w), int(lm[0].y * h)
                    text(frame, g.upper(), (wx - 30, wy + 30), 0.7, (0, 255, 255))

                if g == "pinch":
                    p1 = (int(lm[4].x * w), int(lm[4].y * h))
                    p2 = (int(lm[8].x * w), int(lm[8].y * h))
                    palm = math.hypot((lm[0].x - lm[9].x) * w, (lm[0].y - lm[9].y) * h) or 1
                    ratio = math.hypot(p1[0] - p2[0], p1[1] - p2[1]) / palm
                    last_ratio = ratio
                    span = cfg["max_ratio"] - cfg["min_ratio"]
                    pct = max(0, min(100, (ratio - cfg["min_ratio"]) / span * 100))
                    color = (0, 0, 255) if locked else (255, 0, 255)
                    cv2.line(frame, p1, p2, color, 3)
                    cv2.circle(frame, p1, 9, color, -1)
                    cv2.circle(frame, p2, 9, color, -1)

                    if use_brightness and side == "Left":
                        pinch_brightness = True
                        smooth_b += (pct - smooth_b) * 0.25
                        target_b = smooth_b
                    else:
                        pinch_volume = True
                        smooth_v += (pct - smooth_v) * 0.25
                        target_v = smooth_v

        if locked and gesture != "peace":
            gesture = None
        fired, progress = hold.update(gesture)

        if gesture and progress > 0:
            x0 = w // 2 - 100
            cv2.rectangle(frame, (x0, h - 60), (x0 + int(200 * progress), h - 40), (0, 255, 255), -1)
            cv2.rectangle(frame, (x0, h - 60), (x0 + 200, h - 40), (255, 255, 255), 2)

        if fired:
            if gesture == "fist":
                toggle_mute()
            elif gesture == "peace":
                toggle_lock()
            elif gesture == "rock":
                pyautogui.press("playpause")
                notify("PLAY / PAUSE")

        if not locked:
            if pinch_volume:
                value = round(target_v / 5) * 5 if cfg["snap"] else target_v
                vol.set(value)
            else:
                smooth_v = float(vol.level)

            if pinch_brightness:
                if now - last_bright_set > 0.15 and abs(target_b - bright) >= 2:
                    try:
                        sbc.set_brightness(int(target_b))
                        bright = int(target_b)
                    except Exception:
                        pass
                    last_bright_set = now
            else:
                smooth_b = float(bright)

        bar(frame, 30, "VOL", 0 if vol.muted else vol.level, (0, 0, 255) if vol.muted else (0, 255, 0))
        if use_brightness:
            bar(frame, w - 70, "BRIGHT", bright, (0, 200, 255))

        fps = 1 / (now - prev_time) if prev_time else 0
        prev_time = now
        text(frame, f"FPS {int(fps)}", (w - 120, 30), 0.6, (0, 255, 0))
        text(frame, f"Audio: {vol.mode}", (20, 30), 0.55)
        if locked:
            text(frame, "LOCKED", (20, 60), 0.65, (0, 0, 255))
        if vol.muted:
            text(frame, "MUTED", (20, 90), 0.65, (0, 0, 255))
        if cfg["snap"]:
            text(frame, "SNAP 5%", (20, 120), 0.55, (255, 255, 0))

        if now < message_until:
            (tw, _), _ = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 1.4, 3)
            text(frame, message, ((w - tw) // 2, h // 2), 1.4, (0, 255, 255), 3)

        if cfg["show_help"]:
            for i, line in enumerate(HELP):
                text(frame, line, (110, h - 150 + i * 26), 0.5)

        cv2.imshow("Gesture Control", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break
        elif key == ord("h"):
            cfg["show_help"] = not cfg["show_help"]
        elif key == ord("l"):
            toggle_lock()
        elif key == ord("m"):
            toggle_mute()
        elif key == ord("s"):
            cfg["snap"] = not cfg["snap"]
            notify("SNAP ON" if cfg["snap"] else "SNAP OFF")
        elif key == ord("b") and HAS_BRIGHTNESS:
            use_brightness = not use_brightness
            cfg["brightness"] = use_brightness
            notify("BRIGHTNESS ON" if use_brightness else "BRIGHTNESS OFF")
        elif key == ord("n") and last_ratio:
            cfg["min_ratio"] = last_ratio
            notify("MIN SET")
        elif key == ord("x") and last_ratio:
            cfg["max_ratio"] = last_ratio
            notify("MAX SET")
        elif key == ord("r"):
            cfg["min_ratio"] = DEFAULTS["min_ratio"]
            cfg["max_ratio"] = DEFAULTS["max_ratio"]
            notify("RESET")
        elif key == ord("p"):
            name = f"screenshot_{int(time.time())}.png"
            cv2.imwrite(name, frame)
            notify("SAVED")

    save_config(cfg)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
