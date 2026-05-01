import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
import joblib
from pathlib import Path


# Load dataset
df = pd.read_csv("data\data.csv")

# 2 FEATURES
X = df[['emg1', 'emg2']]
y = df['label']

# Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Pipeline
model = make_pipeline(
    StandardScaler(),
    LogisticRegression(max_iter=1000)
)

# Train
model.fit(X_train, y_train)

print("Accuracy:", model.score(X_test, y_test))


filepath="models/emg_modelv0.3.pkl"
if Path("models/emg_model.pkl").exists():
    filepath=input("models/emg_model.pkl already exist, please enter different name:")

joblib.dump(model, filepath) 

print("✅ NEW 2-FEATURE MODEL SAVED")
