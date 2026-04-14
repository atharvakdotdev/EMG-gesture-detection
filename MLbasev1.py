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
# COOLDOWN_TIME = 1.5  # faster response

MODEL_PATH = "emg_modelv0.2.pkl"
WINDOW = 1
BASELINE_SAMPLES = 500
DEVIATION_THRESHOLD_ENV1 = 5
DEVIATION_THRESHOLD_ENV2 = 50  # tune 8–20
  # tune 8–20
COOLDOWN_TIME = 1


# ===============================
# GLOBALS
# ===============================
ser = None
running = False
last_trigger_time = 0

# timestampCSV = []
# emg1 = []
# emg2 = []
# labels = []

# Load model
model = joblib.load(MODEL_PATH)

window_buffer = deque(maxlen=WINDOW)

# Baseline system
baseline_buffer = deque(maxlen=BASELINE_SAMPLES)
baseline_mean = [0, 0]
baseline_ready = False

# Key mapping
action_keys = {
    "1": "space",
    "2": "left",
    "3": "right"
}

# ===============================
# FEATURE EXTRACTION (2 FEATURES)
# ===============================
def extract_features(window):
    env1, env2 = window[-1]
    return pd.DataFrame([[env1, env2]], columns=['emg1', 'emg2'])

# ===============================
# SERIAL PARSER
# ===============================
def parse_serial(line):
    try:
        line = line.strip().replace(',', '\t')
        parts = line.split('\t')

        if len(parts) < 2:
            return None

        env1 = int(parts[0].strip())
        env2 = int(parts[1].strip())

        if env1 < 0 or env2 < 0:
            return None

        return env1, env2

    except:
        return None

# ===============================
# BASELINE + DEVIATION
# ===============================
def is_deviation(env1, env2):
    global baseline_mean, baseline_ready

    # Collect baseline first
    if not baseline_ready:
        baseline_buffer.append((env1, env2))

        if len(baseline_buffer) == BASELINE_SAMPLES:
            b1 = np.mean([x[0] for x in baseline_buffer])
            b2 = np.mean([x[1] for x in baseline_buffer])
            baseline_mean = [b1, b2]
            baseline_ready = True
            print(f"✅ Baseline locked: {baseline_mean}")

        return False

    # Check deviation
    d1 = abs(env1 - baseline_mean[0])
    d2 = abs(env2 - baseline_mean[1])

    return (d1 > DEVIATION_THRESHOLD_ENV1) or (d2 > DEVIATION_THRESHOLD_ENV2)

# ===============================
# EMG PROCESSING (ML + GATING)
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

        # 🔥 ONLY PREDICT IF DEVIATION DETECTED
        if is_deviation(env1, env2):

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
        # timestampCSV.append(current_time)
        # emg1.append(env1)
        # emg2.append(env2)
        # labels.append(prediction)

        # Debug
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"{timestamp} | Env: {env1}, {env2} | ML: {prediction}")

# ===============================
# PRESETS (UNCHANGED)
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

            return "ML EMG Started 🚀 (Calibrating baseline...)"

        return "Already running"

    def stop_emg(self):
        global running, ser

        running = False

        if ser:
            ser.close()
            ser = None

        

        return "Stopped + Data Saved"

# ===============================
# UI
# ===============================
html_content = """<html><body style='background:black;color:white'>
<h2>ML EMG Controller (Low Latency)</h2>
<button onclick="start()">Start</button>
<button onclick="stop()">Stop</button>
<p>Wait 1–2 sec for baseline calibration</p>
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
