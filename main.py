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
# EMG & Serial Configuration
# ===============================
SERIAL_PORT = "COM3"        # Change this as needed
BAUD_RATE = 115200
BUFFER_SIZE = 64            # Envelope smoothing factor
COOLDOWN_TIME = 0.5
last_trigger_time = 0

# Global serial port and control flag 
ser = None
running = False
timestampCSV=[]
emg1=[]
emg2=[]
lable=[]
# Global key mapping for each action (default keys)
action_keys = {
    "action1": "space",
    "action2": "left",
    "action3": "right"
}

# Circular buffers for smoothing
buffer1 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
buffer2 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

def process_emg_data():
    """Reads envelope data from serial, triggers keypresses, and logs output."""
    global last_trigger_time, running, ser, action_keys

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
                print("Malformed data received")
                continue

            # ✅ NOW these are already ENVELOPES
            env1, env2 = map(int, parts)

            output = "0"

            # Store data
            

            # ===============================
            # 🎯 Gesture Logic (CLEANED)
            # ===============================

            if env1 > 20 and env2 < 100:
                if current_time - last_trigger_time > COOLDOWN_TIME:
                    last_trigger_time = current_time
                    keyboard.press_and_release(action_keys["action1"])
                output = "1"

            elif env2 > 100:
                if env1 > 10 and env2 > 200:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action3"])
                    output = "3"

                elif env2 > 150 and env1 < 10:
                    if current_time - last_trigger_time > COOLDOWN_TIME:
                        last_trigger_time = current_time
                        keyboard.press_and_release(action_keys["action2"])
                    output = "2"
            timestampCSV.append(current_time)
            emg1.append(env1)
            emg2.append(env2)
            lable.append(output)
            # ===============================
            # 🖨️ Debug Print
            # ===============================
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            print(f"{timestamp} | Env: {env1}, {env2} | Output: {output}")

        except ValueError:
            print("Malformed data received")

# ===============================
# JSON Database Functions for Presets
# ===============================
PRESETS_FILE = "presets.json"

def load_presets_from_file():
    """Load presets from the JSON file. Return an empty list if file does not exist."""
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, "r") as f:
            data = json.load(f)
            return data.get("presets", [])
    except Exception as e:
        print("Error loading presets:", e)
        return []

def save_presets_to_file(presets):
    """Save the presets list to the JSON file."""
    try:
        with open(PRESETS_FILE, "w") as f:
            json.dump({"presets": presets}, f, indent=4)
    except Exception as e:
        print("Error saving presets:", e)

# ===============================
# Python API Exposed to JS
# ===============================
class API:
    def __init__(self):
        self.emg_thread = None

    def start_emg(self, key1, key2, key3):
        """Update key mappings from dropdowns and start EMG processing."""
        global running, ser, action_keys
        action_keys["action1"] = key1
        action_keys["action2"] = key2
        action_keys["action3"] = key3
        if not running:
            try:
                ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            except Exception as e:
                print("Error opening serial port:", e)
                return "Error opening serial port"
            running = True
            self.emg_thread = threading.Thread(target=process_emg_data, daemon=True)
            self.emg_thread.start()
            return "EMG Started with keys: " + json.dumps(action_keys)
        else:
            return "EMG is already running"

    def stop_emg(self):
        global running, ser
        running = False
        if ser:
            ser.close()
            ser = None
        with open("data.csv", mode="a", newline="") as file:
          writer = csv.writer(file)    
          for i in range(len(timestampCSV)):
              writer.writerow([timestampCSV[i], emg1[i], emg2[i],2])
        return "EMG Stopped"

    def get_presets(self):
        """Return the list of saved presets."""
        return load_presets_from_file()

    def save_preset(self, name, action1, action2, action3):
        """
        Save a new preset or update an existing one.
        Returns the updated list of presets.
        """
        presets = load_presets_from_file()
        preset_exists = False
        for preset in presets:
            if preset["name"] == name:
                preset["action1"] = action1
                preset["action2"] = action2
                preset["action3"] = action3
                preset_exists = True
                break
        if not preset_exists:
            presets.append({
                "name": name,
                "action1": action1,
                "action2": action2,
                "action3": action3
            })
        save_presets_to_file(presets)
        return presets

    def load_preset(self, name):
        """Return the preset matching the given name."""
        presets = load_presets_from_file()
        for preset in presets:
            if preset["name"] == name:
                return preset
        return {}

# ===============================
# HTML UI with Bootstrap (with inline Save Preset field)
# ===============================
html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>EMG Gesture Control</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    #sidebar { height: 420px; overflow-y: auto; }
  </style>
</head>
<body class="bg-dark text-white">
  <div class="container-fluid p-3">
    <div class="row">
      <!-- Sidebar -->
      
      <!-- Main Content -->
      <div class="col-md-9">
        <div class="d-flex justify-content-around my-3">
          <div class="text-center">
            <label class="fw-bold">Action-one</label>
            <select class="form-select" id="action1Dropdown">
              <option value="esc">Esc</option>
              <option value="f1">F1</option>
              <option value="f2">F2</option>
              <option value="f3">F3</option>
              <option value="f4">F4</option>
              <option value="f5">F5</option>
              <option value="f6">F6</option>
              <option value="f7">F7</option>
              <option value="f8">F8</option>
              <option value="f9">F9</option>
              <option value="f10">F10</option>
              <option value="f11">F11</option>
              <option value="f12">F12</option>
              <option value="print screen">Print Screen</option>
              <option value="scroll lock">Scroll Lock</option>
              <option value="pause">Pause</option>
              <option value="insert">Insert</option>
              <option value="delete">Delete</option>
              <option value="home">Home</option>
              <option value="end">End</option>
              <option value="page up">Page Up</option>
              <option value="page down">Page Down</option>
              <option value="up">Up Arrow</option>
              <option value="down">Down Arrow</option>
              <option value="left">Left Arrow</option>
              <option value="right">Right Arrow</option>
              <option value="space" selected>Space</option>
              <option value="enter">Enter</option>
              <option value="tab">Tab</option>
              <option value="backspace">Backspace</option>
              <option value="caps lock">Caps Lock</option>
              <option value="shift">Shift</option>
              <option value="ctrl">Ctrl</option>
              <option value="alt">Alt</option>
              <option value="alt gr">Alt Gr</option>
              <option value="menu">Menu</option>
              <option value="num lock">Num Lock</option>
              <option value="numpad /">Numpad /</option>
              <option value="numpad *">Numpad *</option>
              <option value="numpad -">Numpad -</option>
              <option value="numpad +">Numpad +</option>
              <option value="numpad enter">Numpad Enter</option>
              <option value="numpad 0">Numpad 0</option>
              <option value="numpad 1">Numpad 1</option>
              <option value="numpad 2">Numpad 2</option>
              <option value="numpad 3">Numpad 3</option>
              <option value="numpad 4">Numpad 4</option>
              <option value="numpad 5">Numpad 5</option>
              <option value="numpad 6">Numpad 6</option>
              <option value="numpad 7">Numpad 7</option>
              <option value="numpad 8">Numpad 8</option>
              <option value="numpad 9">Numpad 9</option>
            </select>
          </div>
          <div class="text-center">
            <label class="fw-bold">Action-two</label>
            <select class="form-select" id="action2Dropdown">
              <option value="esc">Esc</option>
              <option value="f1">F1</option>
              <option value="f2">F2</option>
              <option value="f3">F3</option>
              <option value="f4">F4</option>
              <option value="f5">F5</option>
              <option value="f6">F6</option>
              <option value="f7">F7</option>
              <option value="f8">F8</option>
              <option value="f9">F9</option>
              <option value="f10">F10</option>
              <option value="f11">F11</option>
              <option value="f12">F12</option>
              <option value="print screen">Print Screen</option>
              <option value="scroll lock">Scroll Lock</option>
              <option value="pause">Pause</option>
              <option value="insert">Insert</option>
              <option value="delete">Delete</option>
              <option value="home">Home</option>
              <option value="end">End</option>
              <option value="page up">Page Up</option>
              <option value="page down">Page Down</option>
              <option value="up">Up Arrow</option>
              <option value="down">Down Arrow</option>
              <option value="left" selected>Left Arrow</option>
              <option value="right">Right Arrow</option>
              <option value="space">Space</option>
              <option value="enter">Enter</option>
              <option value="tab">Tab</option>
              <option value="backspace">Backspace</option>
              <option value="caps lock">Caps Lock</option>
              <option value="shift">Shift</option>
              <option value="ctrl">Ctrl</option>
              <option value="alt">Alt</option>
              <option value="alt gr">Alt Gr</option>
              <option value="menu">Menu</option>
              <option value="num lock">Num Lock</option>
              <option value="numpad /">Numpad /</option>
              <option value="numpad *">Numpad *</option>
              <option value="numpad -">Numpad -</option>
              <option value="numpad +">Numpad +</option>
              <option value="numpad enter">Numpad Enter</option>
              <option value="numpad 0">Numpad 0</option>
              <option value="numpad 1">Numpad 1</option>
              <option value="numpad 2">Numpad 2</option>
              <option value="numpad 3">Numpad 3</option>
              <option value="numpad 4">Numpad 4</option>
              <option value="numpad 5">Numpad 5</option>
              <option value="numpad 6">Numpad 6</option>
              <option value="numpad 7">Numpad 7</option>
              <option value="numpad 8">Numpad 8</option>
              <option value="numpad 9">Numpad 9</option>
            </select>
          </div>
          <div class="text-center">
            <label class="fw-bold">Action-three</label>
            <select class="form-select" id="action3Dropdown">
              <option value="esc">Esc</option>
              <option value="f1">F1</option>
              <option value="f2">F2</option>
              <option value="f3">F3</option>
              <option value="f4">F4</option>
              <option value="f5">F5</option>
              <option value="f6">F6</option>
              <option value="f7">F7</option>
              <option value="f8">F8</option>
              <option value="f9">F9</option>
              <option value="f10">F10</option>
              <option value="f11">F11</option>
              <option value="f12">F12</option>
              <option value="print screen">Print Screen</option>
              <option value="scroll lock">Scroll Lock</option>
              <option value="pause">Pause</option>
              <option value="insert">Insert</option>
              <option value="delete">Delete</option>
              <option value="home">Home</option>
              <option value="end">End</option>
              <option value="page up">Page Up</option>
              <option value="page down">Page Down</option>
              <option value="up">Up Arrow</option>
              <option value="down">Down Arrow</option>
              <option value="left">Left Arrow</option>
              <option value="right" selected>Right Arrow</option>
              <option value="space">Space</option>
              <option value="enter">Enter</option>
              <option value="tab">Tab</option>
              <option value="backspace">Backspace</option>
              <option value="caps lock">Caps Lock</option>
              <option value="shift">Shift</option>
              <option value="ctrl">Ctrl</option>
              <option value="alt">Alt</option>
              <option value="alt gr">Alt Gr</option>
              <option value="menu">Menu</option>
              <option value="num lock">Num Lock</option>
              <option value="numpad /">Numpad /</option>
              <option value="numpad *">Numpad *</option>
              <option value="numpad -">Numpad -</option>
              <option value="numpad +">Numpad +</option>
              <option value="numpad enter">Numpad Enter</option>
              <option value="numpad 0">Numpad 0</option>
              <option value="numpad 1">Numpad 1</option>
              <option value="numpad 2">Numpad 2</option>
              <option value="numpad 3">Numpad 3</option>
              <option value="numpad 4">Numpad 4</option>
              <option value="numpad 5">Numpad 5</option>
              <option value="numpad 6">Numpad 6</option>
              <option value="numpad 7">Numpad 7</option>
              <option value="numpad 8">Numpad 8</option>
              <option value="numpad 9">Numpad 9</option>
            </select>
          </div>
        </div>
        <!-- EMG Control Buttons -->
        <div class="d-flex justify-content-center my-3">
          <button onclick="startEMG()" class="btn btn-success mx-2">Start EMG</button>
          <button onclick="stopEMG()" class="btn btn-danger mx-2">Stop EMG</button>
        </div>
        <!-- Output Label -->
        
      </div>
    </div>
  </div>

  <!-- Bootstrap Bundle JS and Custom Script -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    // Start and Stop EMG functions
    function startEMG() {
      var key1 = document.getElementById('action1Dropdown').value;
      var key2 = document.getElementById('action2Dropdown').value;
      var key3 = document.getElementById('action3Dropdown').value;
      window.pywebview.api.start_emg(key1, key2, key3).then(response => {
        console.log(response);
      });
    }
    function stopEMG() {
      window.pywebview.api.stop_emg().then(response => {
        console.log(response);
      });
    }

    // Load presets into the sidebar list
    function loadPresets() {
      window.pywebview.api.get_presets().then(presets => {
        const presetList = document.getElementById('presetList');
        presetList.innerHTML = "";
        presets.forEach(preset => {
          let a = document.createElement('a');
          a.href = "#";
          a.className = "list-group-item list-group-item-action bg-dark text-white d-flex justify-content-between mb-2";
          a.innerHTML = preset.name +
            '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-play-fill" viewBox="0 0 16 16"><path d="m11.596 8.697-6.363 3.692c-.54.313-1.233-.066-1.233-.697V4.308c0-.63.692-1.01 1.233-.696l6.363 3.692a.802.802 0 0 1 0 1.393"/></svg>';
          // Clicking a preset will update the dropdowns with the saved key values.
          a.addEventListener('click', () => {
            document.getElementById('action1Dropdown').value = preset.action1;
            document.getElementById('action2Dropdown').value = preset.action2;
            document.getElementById('action3Dropdown').value = preset.action3;
          });
          presetList.appendChild(a);
        });
      });
    }

    document.addEventListener('DOMContentLoaded', function() {
      loadPresets();
      // Save preset using the inline input field and Save button
      document.getElementById('savePresetBtn').addEventListener('click', function() {
        var presetName = document.getElementById('presetNameInput').value;
        if (!presetName) {
          alert("Please enter a preset name.");
          return;
        }
        var action1 = document.getElementById('action1Dropdown').value;
        var action2 = document.getElementById('action2Dropdown').value;
        var action3 = document.getElementById('action3Dropdown').value;
        window.pywebview.api.save_preset(presetName, action1, action2, action3).then(response => {
          console.log(response);
          document.getElementById('presetNameInput').value = "";
          loadPresets();
        });
      });
      // Optional: clicking the plus button clears the preset name input for new entry.
      document.getElementById('addPresetBtn').addEventListener('click', function() {
        document.getElementById('presetNameInput').value = "";
      });
    });
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    api = API()
    webview.create_window("EMG Gesture Control", html=html_content, js_api=api, width=800, height=600)
    webview.start()
    """
    Features to add:
    Setting:
      check base line
      tune thresholds 
      select com port
      select board
      select buad rate
    Home:
      quick start
      tutorial
    
    preset:
      action groups 
      start stop:
      key press and release / key hold etc
      change name
      
    
    """



    # <div class="col-md-3 p-3 rounded d-flex flex-column" style="background-color: #1F2022; height:420px;">
    #     <!-- Plus Button (for future use or to clear the input) -->
    #     <div class="mt-top">
    #       <a href="#" class="bg-dark text-white d-flex align-items-center" >
    #         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-house-door-fill" viewBox="0 0 16 16">
    #                     <path d="M6.5 14.5v-3.505c0-.245.25-.495.5-.495h2c.25 0 .5.25.5.5v3.5a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.146-.354L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293L8.354 1.146a.5.5 0 0 0-.708 0l-6 6A.5.5 0 0 0 1.5 7.5v7a.5.5 0 0 0 .5.5h4a.5.5 0 0 0 .5-.5"/>
    #                   </svg>Home
    #       </a>
    #     </div>
        
        
    #     <!-- Presets List -->
    #     <div id="presetList" class="list-group mb-3">
    #       <!-- Preset items will be loaded here dynamically -->
    #     </div>
    #     <!-- Settings Link -->
    #     <div class="mt-auto">
    #       <a href="#" class="bg-dark text-white d-flex align-items-center">
    #         <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor"
    #           class="bi bi-gear-fill me-2" viewBox="0 0 16 16">
    #           <path d="M9.405 1.05c-.413-1.4-2.397-1.4-2.81 0l-.1.34a1.464 1.464 0 0 1-2.105.872l-.31-.17c-1.283-.698-2.686.705-1.987 1.987l.169.311c.446.82.023 1.841-.872 2.105l-.34.1c-1.4.413-1.4 2.397 0 2.81l.34.1a1.464 1.464 0 0 1 .872 2.105l-.17.31c-.698 1.283.705 2.686 1.987 1.987l.311-.169a1.464 1.464 0 0 1 2.105.872l.1.34c.413 1.4 2.397 1.4 2.81 0l.1-.34a1.464 1.464 0 0 1 2.105-.872l.31.17c1.283.698 2.686-.705 1.987-1.987l-.169-.311a1.464 1.464 0 0 1 .872-2.105l.34-.1c1.4-.413 1.4-2.397 0-2.81l-.34-.1a1.464 1.464 0 0 1-.872-2.105l.17-.31c.698-1.283-.705-2.686-1.987-1.987l-.311.169a1.464 1.464 0 0 1-2.105-.872zM8 10.93a2.929 2.929 0 1 1 0-5.86 2.929 2.929 0 0 1 0 5.858z"/>
    #         </svg>
    #         Settings
    #       </a>
    #     </div>
    #   </div>
