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

# ===============================
# CONFIG
# ===============================
SERIAL_PORT = "COM3"
BAUD_RATE = 115200

BUFFER_SIZE = 64
COOLDOWN_TIME = 0.5

# 🔥 RECORDING CONFIG
recording_enabled = False
csv_filename = "data.csv"
last_save_time = time.time()
SAVE_INTERVAL = 5  # seconds

# ===============================
# GLOBALS
# ===============================
ser = None
running = False
last_trigger_time = 0

timestampCSV = []
emg1 = []
emg2 = []
lable = []

# Key mappings
action_keys = {
    "action1": "space",
    "action2": "left",
    "action3": "right"
}

# Buffers
buffer1 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
buffer2 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

# ===============================
# CSV SAVE FUNCTION
# ===============================
def save_to_csv():
    global timestampCSV, emg1, emg2, lable, csv_filename

    if not timestampCSV:
        return

    file_exists = os.path.exists(csv_filename)

    with open(csv_filename, "a", newline="") as f:
        writer = csv.writer(f)

        # Add header if file is new
        if not file_exists:
            writer.writerow(["timestamp", "emg1", "emg2", "label"])

        for i in range(len(timestampCSV)):
            writer.writerow([timestampCSV[i], emg1[i], emg2[i], lable[i]])

    # 🔥 CLEAR RAM
    timestampCSV.clear()
    emg1.clear()
    emg2.clear()
    lable.clear()

    print(f"💾 Auto-saved to {csv_filename}")

# ===============================
# EMG LOOP (NON-ML)
# ===============================
def process_emg_data():
    global last_trigger_time, running, ser, action_keys, last_save_time

    while running:
        current_time = time.time()

        try:
            line = ser.readline().decode('utf-8').strip() if ser else ""
        except Exception as e:
            print("Serial read error:", e)
            continue

        if not line:
            continue

        try:
            parts = line.split('\t')
            if len(parts) != 2:
                continue

            env1, env2 = map(int, parts)

            output = "0"

            # ===============================
            # 🎯 GESTURE LOGIC (UNCHANGED)
            # ===============================
            if env1 > 10 and env2 < 100:
                if current_time - last_trigger_time > COOLDOWN_TIME:
                    last_trigger_time = current_time
                    keyboard.press_and_release(action_keys["action1"])
                output = "1"

            elif env2 > 100:
                if env1 > 10 and env2 > 100:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action3"])
                    output = "3"

                elif env2 > 150 and env1 < 10:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action2"])
                    output = "2"

            # ===============================
            # 📊 RECORDING SYSTEM
            # ===============================
            if recording_enabled:
                timestampCSV.append(current_time)
                emg1.append(env1)
                emg2.append(env2)
                lable.append(output)

                if time.time() - last_save_time > SAVE_INTERVAL:
                    save_to_csv()
                    last_save_time = time.time()

            # Debug
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"{timestamp} | {env1}, {env2} -> {output}")

        except:
            continue

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
    with open(PRESETS_FILE, "w") as f:
        json.dump({"presets": presets}, f, indent=4)

# ===============================
# API
# ===============================
class API:
    def __init__(self):
        self.emg_thread = None

    def toggle_recording(self, enable, filename):
        global recording_enabled, csv_filename

        recording_enabled = enable

        if filename:
            csv_filename = filename

        return f"Recording {'ON' if enable else 'OFF'} → {csv_filename}"

    def start_emg(self, key1, key2, key3):
        global running, ser, action_keys

        action_keys["action1"] = key1
        action_keys["action2"] = key2
        action_keys["action3"] = key3

        if not running:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)
            except Exception as e:
                return str(e)

            running = True
            self.emg_thread = threading.Thread(target=process_emg_data, daemon=True)
            self.emg_thread.start()

            return "EMG Started 🚀"

        return "Already running"

    def stop_emg(self):
        global running, ser

        running = False

        if ser:
            ser.close()
            ser = None

        # 🔥 FINAL SAVE
        save_to_csv()

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
# LOAD UI
# ===============================
with open("templates/index.html", "r") as file:
    html_content = file.read()

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
