import webview
import threading
import serial
import numpy as np
import time
from collections import deque
import keyboard
import json
import os
import csv
from dotenv import load_dotenv
import os

load_dotenv()

# Optional ML imports
try:
    import joblib
    import pandas as pd
except:
    joblib = None

# ===============================
# CONFIG
# ===============================

SERIAL_PORT = os.getenv("SERIAL_PORT", "COM3")
BAUD_RATE = int(os.getenv("BAUD_RATE", 115200))

MODEL_PATH = os.getenv("MODEL_PATH", "emg_modelv0.2.pkl")
FORCE_MODE = os.getenv("FORCE_MODE", "auto")

BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", 64))
COOLDOWN_TIME = float(os.getenv("COOLDOWN_TIME", 0.5))

# ML config
WINDOW = int(os.getenv("WINDOW", 1))
BASELINE_SAMPLES = int(os.getenv("BASELINE_SAMPLES", 300))
DEV1 = int(os.getenv("DEV1", 5))
DEV2 = int(os.getenv("DEV2", 40))

# Recording
recording_enabled = False
csv_filename = os.getenv("CSV_FILENAME", "data.csv")
SAVE_INTERVAL = int(os.getenv("SAVE_INTERVAL", 5))
last_save_time = time.time()
running=False
timestampCSV, emg1, emg2, labels = [], [], [], []
last_trigger_time = 0

action_keys = {
    "action1": "space",
    "action2": "left",
    "action3": "right"
}

# Buffers
buffer1 = deque([0]*BUFFER_SIZE, maxlen=BUFFER_SIZE)
buffer2 = deque([0]*BUFFER_SIZE, maxlen=BUFFER_SIZE)

window_buffer = deque(maxlen=WINDOW)
baseline_buffer = deque(maxlen=BASELINE_SAMPLES)
baseline_mean = [0, 0]
baseline_ready = False


model = None
MODE = "non-ml"

if FORCE_MODE == "ml":
    MODE = "ml"

elif FORCE_MODE == "non-ml":
    MODE = "non-ml"

else:  # auto
    if joblib and os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            MODE = "ml"
        except Exception as e:
            print("⚠️ Model load failed:", e)
            MODE = "non-ml"


print(f"""
=== CONFIG ===
PORT: {SERIAL_PORT}
BAUD: {BAUD_RATE}
MODE: {FORCE_MODE}
MODEL: {MODEL_PATH}
=============
""")

# ===============================
# HELPERS
# ===============================
def save_to_csv():
    global timestampCSV, emg1, emg2, labels

    if not timestampCSV:
        return

    file_exists = os.path.exists(csv_filename)

    with open(csv_filename, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(["timestamp", "emg1", "emg2", "label"])

        for i in range(len(timestampCSV)):
            writer.writerow([timestampCSV[i], emg1[i], emg2[i], labels[i]])

    timestampCSV.clear()
    emg1.clear()
    emg2.clear()
    labels.clear()

# ===============================
# ML FUNCTIONS
# ===============================
def extract_features(window):
    env1, env2 = window[-1]
    return pd.DataFrame([[env1, env2]], columns=['emg1', 'emg2'])

def is_deviation(env1, env2):
    global baseline_ready, baseline_mean

    if not baseline_ready:
        baseline_buffer.append((env1, env2))
        if len(baseline_buffer) == BASELINE_SAMPLES:
            baseline_mean[0] = np.mean([x[0] for x in baseline_buffer])
            baseline_mean[1] = np.mean([x[1] for x in baseline_buffer])
            baseline_ready = True
        return False

    return (abs(env1 - baseline_mean[0]) > DEV1 or
            abs(env2 - baseline_mean[1]) > DEV2)

# ===============================
# MAIN LOOP (UNIFIED)
# ===============================
def process_emg_data():
    global running, ser, last_trigger_time, last_save_time

    while running:
        try:
            line = ser.readline().decode('utf-8', errors='ignore')
        except:
            continue

        parts = line.strip().replace(',', '\t').split('\t')
        if len(parts) < 2:
            continue

        try:
            env1, env2 = int(parts[0]), int(parts[1])
        except:
            continue

        current_time = time.time()
        output = "0"

        # ===============================
        # 🔥 ML MODE
        # ===============================
        if MODE == "ml" and model:
            window_buffer.append((env1, env2))

            if is_deviation(env1, env2) and len(window_buffer) == WINDOW:
                try:
                    features = extract_features(window_buffer)
                    pred = str(model.predict(features)[0])
                    output = pred

                    key = action_keys.get(f"action{pred}")

                    if key and current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(key)

                except:
                    pass

        # ===============================
        # 🔥 NON-ML MODE
        # ===============================
        else:
            if env1 > 10 and env2 < 100:
                if current_time - last_trigger_time > COOLDOWN_TIME:
                    last_trigger_time = current_time
                    keyboard.press_and_release(action_keys["action1"])
                output = "1"

            elif env2 > 100:
                if env1 > 10:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action3"])
                    output = "3"
                elif env2 > 150:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action2"])
                    output = "2"

        # ===============================
        # 📊 RECORDING
        # ===============================
        if recording_enabled:
            timestampCSV.append(current_time)
            emg1.append(env1)
            emg2.append(env2)
            labels.append(output)

            if time.time() - last_save_time > SAVE_INTERVAL:
                save_to_csv()
                last_save_time = time.time()

        # ===============================
        # 🖥️ CLEAN DEBUG LINE
        # ===============================
        print(f"\r{env1:4d}, {env2:4d} -> {output} [{MODE}]", end="", flush=True)

# ===============================
# API
# ===============================
class API:
    def __init__(self):
        self.thread = None

    def toggle_recording(self, enable, filename):
        global recording_enabled, csv_filename
        recording_enabled = enable
        if filename:
            csv_filename = filename
        return f"Recording {'ON' if enable else 'OFF'}"

    def start_emg(self, k1, k2, k3):
        global running, ser, action_keys, baseline_ready

        action_keys["action1"] = k1
        action_keys["action2"] = k2
        action_keys["action3"] = k3
        baseline_ready = False

        if not running:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
            except Exception as e:
                return str(e)

            running = True
            self.thread = threading.Thread(target=process_emg_data, daemon=True)
            self.thread.start()

            return f"Started in {MODE} mode 🚀"

        return "Already running"

    def stop_emg(self):
        global running, ser
        running = False

        if ser:
            ser.close()
            ser = None

        save_to_csv()
        print("\nStopped.")

        return "Stopped"

    

# ===============================
# LOAD UI
# ===============================
with open("templates/index.html", "r") as f:
    html_content = f.read()

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    api = API()
    webview.create_window(
        "EMG Gesture Control",
        html=html_content,
        js_api=api,
        width=900,
        height=650
    )
    webview.start()
