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

recording_enabled = False
csv_filename = "data.csv"
last_save_time = time.time()
SAVE_INTERVAL = 5  # seconds

SERIAL_PORT = "COM3"
BAUD_RATE = 115200

MODEL_PATH = "emg_modelv0.2.pkl"

WINDOW = 1
BASELINE_SAMPLES = 300
DEVIATION_THRESHOLD_ENV1 = 5
DEVIATION_THRESHOLD_ENV2 = 40
COOLDOWN_TIME = 0.8

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

model = joblib.load(MODEL_PATH)

window_buffer = deque(maxlen=WINDOW)

baseline_buffer = deque(maxlen=BASELINE_SAMPLES)
baseline_mean = [0, 0]
baseline_ready = False

# 🔥 SAME STRUCTURE AS YOUR UI
action_keys = {
    "action1": "space",
    "action2": "left",
    "action3": "right"
}

# ===============================
# FEATURE EXTRACTION
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

        return int(parts[0]), int(parts[1])
    except:
        return None

# ===============================
# BASELINE + DEVIATION
# ===============================
def is_deviation(env1, env2):
    global baseline_ready, baseline_mean

    if not baseline_ready:
        baseline_buffer.append((env1, env2))

        if len(baseline_buffer) == BASELINE_SAMPLES:
            baseline_mean[0] = np.mean([x[0] for x in baseline_buffer])
            baseline_mean[1] = np.mean([x[1] for x in baseline_buffer])
            baseline_ready = True
            print("✅ Baseline locked:", baseline_mean)

        return False

    d1 = abs(env1 - baseline_mean[0])
    d2 = abs(env2 - baseline_mean[1])

    return (d1 > DEVIATION_THRESHOLD_ENV1) or (d2 > DEVIATION_THRESHOLD_ENV2)

# ===============================
# EMG LOOP (ML VERSION)
# ===============================
def process_emg_data():
    global running, ser, last_trigger_time

    while running:
        current_time = time.time()

        try:
            line = ser.readline().decode('utf-8', errors='ignore')
        except Exception as e:
            print("Serial error:", e)
            continue

        parsed = parse_serial(line)
        if not parsed:
            continue

        env1, env2 = parsed
        window_buffer.append((env1, env2))

        prediction = "0"

        if is_deviation(env1, env2):

            if len(window_buffer) == WINDOW:
                try:
                    features = extract_features(window_buffer)
                    pred = model.predict(features)[0]
                    prediction = str(pred)

                    # 🔥 MAP ML → UI ACTIONS
                    if prediction == "1":
                        key = action_keys["action1"]
                    elif prediction == "2":
                        key = action_keys["action2"]
                    elif prediction == "3":
                        key = action_keys["action3"]
                    else:
                        key = None

                    if key:
                        if current_time - last_trigger_time > COOLDOWN_TIME:
                            last_trigger_time = current_time
                            keyboard.press_and_release(key)

                except Exception as e:
                    print("Prediction error:", e)

        # Save data
        if recording_enabled:
            timestampCSV.append(current_time)
            emg1.append(env1)
            emg2.append(env2)
            labels.append(prediction)

            # 🔥 AUTO SAVE EVERY 5 SEC
            global last_save_time
            if time.time() - last_save_time > SAVE_INTERVAL:
                save_to_csv()
                last_save_time = time.time()


        print(f"{env1}, {env2} -> {prediction}")

# ===============================
# PRESETS (UNCHANGED)
# ===============================
PRESETS_FILE = "presets.json"
def save_to_csv():
    global timestampCSV, emg1, emg2, labels, csv_filename

    if not timestampCSV:
        return

    with open(csv_filename, "a", newline="") as f:
        writer = csv.writer(f)
        for i in range(len(timestampCSV)):
            writer.writerow([timestampCSV[i], emg1[i], emg2[i], labels[i]])

    # 🔥 CLEAR RAM AFTER SAVE
    timestampCSV.clear()
    emg1.clear()
    emg2.clear()
    labels.clear()

    print(f"💾 Auto-saved to {csv_filename}")

def load_presets_from_file():
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f).get("presets", [])
    except:
        return []

def save_presets_to_file(presets):
    with open(PRESETS_FILE, "w") as f:
        json.dump({"presets": presets}, f, indent=4)

# ===============================
# API (CONNECTS UI)
# ===============================
class API:
    def __init__(self):
        self.thread = None
    def toggle_recording(self, enable, filename):
        global recording_enabled, csv_filename

        recording_enabled = enable

        if filename:
            csv_filename = filename

        return f"Recording {'ON' if enable else 'OFF'} → {csv_filename}"

    def start_emg(self, key1, key2, key3):
        global running, ser, action_keys, baseline_ready

        action_keys["action1"] = key1
        action_keys["action2"] = key2
        action_keys["action3"] = key3

        baseline_ready = False

        if not running:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            except Exception as e:
                return str(e)

            running = True
            self.thread = threading.Thread(target=process_emg_data, daemon=True)
            self.thread.start()

            return "ML EMG Started 🚀 (Calibrating baseline...)"

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

    def get_presets(self):
        return load_presets_from_file()

    def save_preset(self, name, action1, action2, action3):
        presets = load_presets_from_file()

        presets.append({
            "name": name,
            "action1": action1,
            "action2": action2,
            "action3": action3
        })

        save_presets_to_file(presets)
        return presets

# ===============================
# 🔥 YOUR ORIGINAL UI (UNCHANGED)
# ===============================

with open("templates\index.html","r") as file:
    html_content= file.read()
# ===============================
# MAIN
# ===============================
if __name__ == "__main__":
    api = API()
    webview.create_window("EMG Gesture Control", html=html_content, js_api=api, width=800, height=600)
    webview.start()
