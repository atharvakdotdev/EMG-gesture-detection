

---

# **EMG Gesture Control System**

This Python project allows users to map Electromyography (EMG) signals to keyboard actions. It reads real-time EMG data via serial communication, processes it, and triggers keyboard actions based on signal thresholds.

---

## **Features**
- Reads EMG signals from a serial port.
- Smooths signal data using a moving average filter.
- Triggers keyboard actions based on processed EMG signals.
- Allows users to configure key mappings through a web interface.
- Supports saving and loading custom key-mapping presets.

---

## **Dependencies**
Make sure you have the following Python libraries installed:

```sh
pip install pyserial numpy keyboard pywebview
```

---

## **How It Works**
1. **EMG Data Processing:**
   - The system reads two EMG signal values from the serial port.
   - A moving average filter is applied to smooth the signal.
   - If the signal crosses certain thresholds, a corresponding keyboard action is triggered.

2. **Keyboard Actions:**
   - Three actions (`action1`, `action2`, and `action3`) are mapped to specific keys.
   - Default mappings:
     - `action1`: Space key (`"space"`)
     - `action2`: Left arrow (`"left"`)
     - `action3`: Right arrow (`"right"`)

3. **Web Interface:**
   - Users can change key mappings using a dropdown menu.
   - Custom configurations can be saved as presets.
   - The interface is built with Bootstrap for a clean layout.


---

## **Usage**
### **1. Connect Your EMG Device**
Ensure your EMG hardware is connected to the correct serial port. Update `SERIAL_PORT` in the script if necessary.

```python
SERIAL_PORT = "COM3"  # Change this to match your device
BAUD_RATE = 115200
```

### **2. Run the Program**
```sh
python readme.py
```
This will start a local web-based interface.

### **3. Configure Key Bindings**
- Open the web interface.
- Select the desired key mappings from the dropdown menu.
- Click "Start EMG" to begin signal processing.
- Click "Stop EMG" to halt processing.

### **4. Save & Load Presets**
- To save a preset, enter a name and click "Save Preset."
- To load a saved preset, select it from the preset list.

---

## **Customization**
Modify `process_emg_data()` to adjust signal processing logic:

```python
if raw1 > 20 and envelope2 < 50:
    keyboard.press_and_release(action_keys["action1"])  # Trigger "action1"
```
Change the thresholds as needed.

---

## **Troubleshooting**
- **No response from the serial port?** Ensure your device is connected and update the `SERIAL_PORT` value.
- **Unexpected key presses?** Adjust the signal thresholds in `process_emg_data()`.
- **Web interface not opening?** Make sure all dependencies are installed.

---

