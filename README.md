

# EMG Gesture Control

A Python-based EMG gesture control system that reads real-time EMG signals from Arduino via serial, and triggers keyboard inputs using either rule-based logic or a machine learning model.

---
## Credits / Inspiration

This project is heavily inspired by the work of Upsidedownlabs and their open-source neuroscience and EMG projects. Their hardware ecosystem and educational content played a major role in the development of this project.

Similar project video by Upside Down Labs:  
[Watch on YouTube](https://www.youtube.com/watch?v=zJ_Ei5tvHiQ)

Their work on EMG sensing, BioAmp hardware, and human-computer interaction projects is highly recommended for anyone interested in biosignal processing and gesture recognition.


## Demo / What it does

`EMG Gesture Control` connects an EMG sensor setup to your PC. It reads live muscle signals, processes them, and translates gestures into keyboard events. The app supports:

- fast non-ML gesture logic
- ML-based prediction with baseline calibration
- auto-switching between modes when a model is available
- live debug output in the terminal
- recording EMG data to CSV
- configurable key mappings and presets via a web UI

---

## Features

- Real-time EMG signal acquisition over serial
- Dual mode operation:
  - Non-ML threshold-based detection
  - ML model prediction pipeline
- Auto mode selects ML automatically if a model file is present
- Configurable via .env
- EMG data recording to `data/*.csv`
- Preset key mapping support via JSON
- Clean single-line live debug output
- Simple pywebview UI for control and settings

---

## How it works

### EMG input
The system reads two EMG channels from the Arduino. Each sample is parsed from the serial stream and treated as enveloped EMG signal values.

### Serial communication
app.py opens the serial port configured by `SERIAL_PORT` and `BAUD_RATE`. Incoming lines are decoded, split into values, and passed into the gesture processing loop.

### Non-ML logic
In non-ML mode, the app applies rule-based thresholds to Envelop EMG values:

- one gesture when `env1` is above a low threshold and `env2` stays under a value
- second gestures when `env2` crosses higher thresholds
- third geust
- actions are mapped to keyboard keys with a cooldown to avoid repeat triggers

This mode is fast and useful for basic EMG control without a trained model.

### ML pipeline
In ML mode, the pipeline is:

1. collect a baseline from the first `BASELINE_SAMPLES`
2. compute whether the current EMG signal deviates from baseline
3. build a feature vector (`emg1`, `emg2`)
4. run `model.predict(...)`
5. map the predicted class to a keyboard action

ML mode uses `joblib` to load the model and `pandas` for feature framing.

---
## Hardware setup [Setup Tutorial](HARDWARE.md)


## Installation

```bash
python -m pip install -r req.txt
```

If you prefer a `requirements.txt`, create one from req.txt or install directly:

```bash
python -m pip install pyserial numpy pandas joblib python-dotenv pywebview keyboard
```

---

## Configuration

Create a .config file in the project root with the following values.

```env
SERIAL_PORT=COM3
BAUD_RATE=115200
FORCE_MODE=auto
MODEL_PATH=models/emg_modelv0.2.pkl
BUFFER_SIZE=64
COOLDOWN_TIME=0.5
WINDOW=1
BASELINE_SAMPLES=300
DEV1=5
DEV2=40
CSV_FILENAME=data.csv
SAVE_INTERVAL=5
```

### .env keys

- `SERIAL_PORT`
  - the Arduino serial port, e.g. `COM3`
- `BAUD_RATE`
  - communication speed, typically `115200`
- `FORCE_MODE`
  - `auto` → auto-selects ML if model exists
  - `ml` → force ML mode
  - `non-ml` → force rule-based mode
- `MODEL_PATH`
  - path to the saved ML model file
- `BUFFER_SIZE`
  - serial smoothing buffer length
- `COOLDOWN_TIME`
  - minimum seconds between triggered key presses
- `WINDOW`
  - ML window size for feature extraction
- `BASELINE_SAMPLES`
  - number of samples collected before ML predictions begin
- `DEV1`
  - baseline deviation threshold for channel 1
- `DEV2`
  - baseline deviation threshold for channel 2
- `CSV_FILENAME`
  - output CSV name when recording
- `SAVE_INTERVAL`
  - seconds between automatic CSV flushes

> Note: non-ML gesture thresholds are currently defined in app.py and can be tuned there if needed.

---

## Usage

### Run the app

```bash
python app.py
```

### Start EMG
- Open the local UI served by `pywebview`
- Choose your key mappings
- Click `Start EMG`

### Key mapping
- Assign actions to physical keys through the UI
- The default mapping is:
  - `action1` → `space`
  - `action2` → `left`
  - `action3` → `right`

---

## Modes Explained

### ML mode
- Loads a trained model from `MODEL_PATH`
- Uses baseline calibration
- Applies prediction on a feature window
- Best for gesture classification after training

### Non-ML mode
- Uses fixed threshold logic
- Fast and lightweight
- Good for prototyping or when a model is unavailable

### Auto mode
- Default mode
- If `MODEL_PATH` exists and loads successfully, ML mode is selected
- Otherwise, falls back to non-ML

---

## Training your own model

### Collect data
1. Enable recording in the UI
2. Perform gestures while the system logs EMG values
3. Save data to CSV

### CSV format
The app writes rows like:

```csv
timestamp,emg1,emg2,label
...
```

- `timestamp`: epoch seconds
- `emg1`, `emg2`: raw EMG channel values
- `label`: gesture class or action ID

### Basic training idea
- collect labeled EMG samples
- build a dataset with `emg1` and `emg2`
- train a classifier to predict gesture labels
- save the model with `joblib`
- point `MODEL_PATH` to the saved `.pkl`

This repo does not include a training script, but a simple sklearn workflow is sufficient:
- `train_test_split`
- `StandardScaler`
- classifier like `RandomForestClassifier` or `LogisticRegression`
- `joblib.dump(model, "models/emg_model.pkl")`

---

## Debugging Guide

### Serial issues
- confirm Arduino is connected
- verify `SERIAL_PORT` and `BAUD_RATE`
- check device manager for the correct COM port

### No input detected
- ensure the EMG electrodes are attached correctly
- verify the Arduino sketch is outputting two numeric values per line
- check the terminal for malformed serial lines

### Delay issues
- reduce `COOLDOWN_TIME`
- lower `WINDOW` if ML mode feels too slow
- keep serial baud rate at `115200`

### Model not loading
- make sure `joblib` is installed
- ensure `MODEL_PATH` points to a valid `.pkl`
- inspect error output when the app starts

---

## Performance Tips

- use `BAUD_RATE=115200`
- keep `BUFFER_SIZE` small for faster responsiveness
- reduce `SAVE_INTERVAL` only if you need frequent CSV writes
- use `non-ml` mode for the lowest latency
- tune `DEV1` / `DEV2` and baseline sample counts for your hardware setup

---

## Contributing

Contributions are welcome.

- open issues for bugs or feature requests
- submit PRs for new gesture modes, config options, or improved UI
- keep changes small and focused
- document .env updates and model requirements

---

## License

Suggested license: MIT

> A permissive license that allows reuse, modification, and sharing while protecting contributors.

---

## Future improvements

- add a dedicated training script
- support more EMG channels
- add a more advanced UI for presets and live graphs
- expose a calibration wizard
- support custom non-ML thresholds in .env
- add a model evaluation dashboard