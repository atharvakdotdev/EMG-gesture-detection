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
import joblib
import pandas as pd

# ===============================
# CONFIG
# ===============================
SERIAL_PORT = "COM3"
BAUD_RATE = 115200
COOLDOWN_TIME = 0.5

MODEL_PATH = "emg_model.pkl"
WINDOW = 1

# ===============================
# GLOBALS
# ===============================
ser = None
running = False
last_trigger_time = 0

timestampCSV = []
emg1 = []
emg2 = []
labels = []

# Load model (supports pipeline or plain model)
model = joblib.load(MODEL_PATH)

window_buffer = deque(maxlen=WINDOW)

action_keys = {
    "1": "space",
    "2": "left",
    "3": "right"
}

# ===============================
# FEATURE EXTRACTION
# ===============================
def extract_features(window):
    emg1_vals = [x[0] for x in window]
    emg2_vals = [x[1] for x in window]

    features = [
        np.mean(emg1_vals),
        np.mean(emg2_vals),
        np.max(emg1_vals),
        np.max(emg2_vals),
        np.std(emg1_vals),
        np.std(emg2_vals),
        np.mean(emg1_vals) / (np.mean(emg2_vals) + 1e-6),
        emg1_vals[-1] - emg1_vals[0],
        emg2_vals[-1] - emg2_vals[0],
    ]

    return pd.DataFrame([features])  # ✅ FIX: avoids sklearn warning

# ===============================
# SERIAL PARSER (FIXED)
# ===============================
def parse_serial(line):
    try:
        line = line.strip()
        line = line.replace(',', '\t')

        parts = line.split('\t')

        if len(parts) < 2:
            return None

        env1 = int(parts[0].strip())
        env2 = int(parts[1].strip())

        # sanity filter
        if env1 < 0 or env2 < 0:
            return None

        return env1, env2

    except:
        print(f"Malformed data: {repr(line)}")
        return None

# ===============================
# EMG PROCESSING (ML ONLY)
# ===============================
def process_emg_data():
    global running, ser, last_trigger_time

    while running:
        current_time = time.time()

        try:
            line = ser.readline().decode('utf-8', errors='ignore')
        except Exception as e:
            print("Serial read error:", e)
            continue

        if not line:
            continue

        parsed = parse_serial(line)
        if not parsed:
            continue

        env1, env2 = parsed

        window_buffer.append((env1, env2))

        prediction = "0"

        if len(window_buffer) == WINDOW:
            try:
                features = extract_features(window_buffer)

                pred = model.predict(features)[0]
                prediction = str(pred)

                # Trigger key
                if prediction in action_keys:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys[prediction])

            except Exception as e:
                print("Prediction error:", e)

        # Save data
        timestampCSV.append(current_time)
        emg1.append(env1)
        emg2.append(env2)
        labels.append(prediction)

        # Debug
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"{timestamp} | Env: {env1}, {env2} | ML: {prediction}")

# ===============================
# PRESETS
# ===============================
PRESETS_FILE = "presets.json"

def load_presets_from_file():
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f).get("presets", [])
    except:
        return []

def save_presets_to_file(presets):
    try:
        with open(PRESETS_FILE, "w") as f:
            json.dump({"presets": presets}, f, indent=4)
    except:
        pass

# ===============================
# API
# ===============================
class API:
    def __init__(self):
        self.emg_thread = None

    def start_emg(self, key1, key2, key3):
        global running, ser, action_keys

        action_keys["1"] = key1
        action_keys["2"] = key2
        action_keys["3"] = key3

        if not running:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            except Exception as e:
                return f"Serial error: {e}"

            running = True
            self.emg_thread = threading.Thread(target=process_emg_data, daemon=True)
            self.emg_thread.start()

            return "ML EMG Started 🚀"

        return "Already running"

    def stop_emg(self):
        global running, ser

        running = False

        if ser:
            ser.close()
            ser = None

        with open("data.csv", "a", newline="") as f:
            writer = csv.writer(f)
            for i in range(len(timestampCSV)):
                writer.writerow([timestampCSV[i], emg1[i], emg2[i], labels[i]])

        return "Stopped + Data Saved"

# ===============================
# UI
# ===============================
html_content = """<html><body style='background:black;color:white'>
<h2>ML EMG Controller Running</h2>
<button onclick="start()">Start</button>
<button onclick="stop()">Stop</button>
<script>
function start(){window.pywebview.api.start_emg("space","left","right")}
function stop(){window.pywebview.api.stop_emg()}
</script>
</body></html>"""

# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    api = API()
    webview.create_window("ML EMG Controller", html=html_content, js_api=api)
    webview.start()
