import joblib
import numpy as np



import serial
import numpy as np
import time
from collections import deque

# ===============================
# EMG & Serial Configuration
# ===============================
SERIAL_PORT = "COM3"  # Change this as needed
BAUD_RATE = 115200
BUFFER_SIZE = 64  # Envelope smoothing factor
# Load trained model and scaler
model = joblib.load("emg_gesture_model.pkl")
scaler = joblib.load("emg_scaler.pkl")
# New EMG data (replace with actual values)
# Global serial port
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

# Circular buffers for smoothing
buffer1 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)
buffer2 = deque([0] * BUFFER_SIZE, maxlen=BUFFER_SIZE)

def get_envelope(data_buffer, new_value):
    """Compute envelope using a moving average."""
    data_buffer.append(new_value)
    return np.mean(data_buffer) * 2  # Adjust scaling factor as needed

def process_emg_data():
    """Reads serial data and computes envelopes."""
    while True:
        try:
            line = ser.readline().decode('utf-8').strip()
            if not line:
                continue
            
            parts = line.split('\t')
            if len(parts) != 2:
                print("Malformed data received")
                continue
            
            raw1, raw2 = map(int, parts)
            envelope1 = get_envelope(buffer1, abs(raw1))
            envelope2 = get_envelope(buffer2, abs(raw2))
            new_emg_data = np.array([[envelope1, envelope2]])


            # Scale data using the same scaler
            new_emg_scaled = scaler.transform(new_emg_data)

            # Predict gesture label
            predicted_label = model.predict(new_emg_scaled)
            print("Predicted Gesture Label:", predicted_label[0])
            print(f"Raw: {raw1}, {raw2} | Envelope: {envelope1:.2f}, {envelope2:.2f}")
        except Exception as e:
            print("Error reading serial data:", e)
            break

# Start processing EMG data
process_emg_data()