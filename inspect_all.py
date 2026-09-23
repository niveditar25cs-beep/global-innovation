import joblib
import pandas as pd
import numpy as np
import sklearn
import sys

print('=== VERSIONS ===')
print(f'scikit-learn: {sklearn.__version__}')
print(f'joblib: {joblib.__version__}')
print(f'pandas: {pd.__version__}')
print(f'numpy: {np.__version__}')
print()

# Inspect CSVs
csvs = ['Alarm.csv', 'CurrentVoltage.csv', 'Power.csv', 'PowerFactor.csv', 'TotalPower.csv']
for csv in csvs:
    try:
        df = pd.read_csv(csv)
        print(f'=== {csv} ===')
        print(f'Shape: {df.shape}')
        print(f'Columns: {list(df.columns)}')
        print()
    except Exception as e:
        print(f'{csv}: ERROR - {e}')

print('=== MODEL INSPECTION ===')

# Load classification model
try:
    clf = joblib.load('transformer_alarm_model.joblib')
    print(f'Classification model type: {type(clf).__name__}')
    if hasattr(clf, 'feature_names_in_'):
        print(f'Feature names: {list(clf.feature_names_in_)}')
        print(f'Feature count: {len(clf.feature_names_in_)}')
    if hasattr(clf, 'classes_'):
        print(f'Classes: {clf.classes_}')
    if hasattr(clf, 'n_estimators'):
        print(f'n_estimators: {clf.n_estimators}')
    print()
except Exception as e:
    print(f'Classification model error: {e}')

# Load regression model
try:
    reg = joblib.load('transformer_temp_model.joblib')
    print(f'Regression model type: {type(reg).__name__}')
    if hasattr(reg, 'feature_names_in_'):
        print(f'Reg Feature names: {list(reg.feature_names_in_)}')
        print(f'Reg Feature count: {len(reg.feature_names_in_)}')
    print()
except Exception as e:
    print(f'Regression model error: {e}')

# Load anomaly detector
try:
    anom = joblib.load('anomaly_detector.joblib')
    print(f'Anomaly detector type: {type(anom).__name__}')
    if hasattr(anom, 'feature_names_in_'):
        print(f'Anomaly Feature names: {list(anom.feature_names_in_)}')
    if hasattr(anom, 'n_features_in_'):
        print(f'Anomaly n_features_in_: {anom.n_features_in_}')
    print()
except Exception as e:
    print(f'Anomaly detector error: {e}')

# Load cls scaler
try:
    scaler = joblib.load('cls_scaler.joblib')
    print(f'Classification scaler type: {type(scaler).__name__}')
    if hasattr(scaler, 'feature_names_in_'):
        print(f'CLS Scaler features: {list(scaler.feature_names_in_)}')
    if hasattr(scaler, 'n_features_in_'):
        print(f'CLS Scaler n_features: {scaler.n_features_in_}')
    print()
except Exception as e:
    print(f'CLS scaler error: {e}')

# Load reg scaler
try:
    rscaler = joblib.load('reg_scaler.joblib')
    print(f'Regression scaler type: {type(rscaler).__name__}')
    if hasattr(rscaler, 'feature_names_in_'):
        print(f'REG Scaler features: {list(rscaler.feature_names_in_)}')
    if hasattr(rscaler, 'n_features_in_'):
        print(f'REG Scaler n_features: {rscaler.n_features_in_}')
    print()
except Exception as e:
    print(f'REG scaler error: {e}')

print('Done.')
sys.stdout.flush()
