"""
Inspect model files and CSV headers using only joblib, numpy, and csv module.
No pandas dependency (blocked by Application Control policy on this machine).
"""
import joblib
import numpy as np
import csv
import json
import sys

print("=== VERSIONS ===")
import sklearn
print(f"scikit-learn: {sklearn.__version__}")
print(f"joblib: {joblib.__version__}")
print(f"numpy: {np.__version__}")
print()

# ─── CSV HEADERS ───────────────────────────────────────────────
csvs = ['Alarm.csv', 'CurrentVoltage.csv', 'Power.csv', 'PowerFactor.csv', 'TotalPower.csv']
for csv_file in csvs:
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)
            row1 = next(reader)
            row2 = next(reader)
        print(f"=== {csv_file} ===")
        print(f"Columns ({len(headers)}): {headers}")
        print(f"Row1: {row1}")
        print(f"Row2: {row2}")
        print()
    except Exception as e:
        print(f"{csv_file}: ERROR - {e}")

# ─── CLASSIFICATION MODEL ───────────────────────────────────────
print("=== transformer_alarm_model.joblib ===")
try:
    clf = joblib.load('transformer_alarm_model.joblib')
    print(f"Type: {type(clf).__name__}")
    print(f"Module: {type(clf).__module__}")
    if hasattr(clf, 'feature_names_in_'):
        feats = list(clf.feature_names_in_)
        print(f"feature_names_in_ ({len(feats)}): {feats}")
    else:
        print("No feature_names_in_ attribute")
        if hasattr(clf, 'n_features_in_'):
            print(f"n_features_in_: {clf.n_features_in_}")
    if hasattr(clf, 'classes_'):
        print(f"classes_: {clf.classes_}")
    if hasattr(clf, 'n_estimators'):
        print(f"n_estimators: {clf.n_estimators}")
    if hasattr(clf, 'steps'):
        print(f"Pipeline steps: {[s[0] for s in clf.steps]}")
        for name, step in clf.steps:
            print(f"  Step '{name}': {type(step).__name__}")
            if hasattr(step, 'feature_names_in_'):
                print(f"    feature_names_in_: {list(step.feature_names_in_)}")
    print()
except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
    print()

# ─── REGRESSION MODEL ──────────────────────────────────────────
print("=== transformer_temp_model.joblib ===")
try:
    reg = joblib.load('transformer_temp_model.joblib')
    print(f"Type: {type(reg).__name__}")
    print(f"Module: {type(reg).__module__}")
    if hasattr(reg, 'feature_names_in_'):
        feats = list(reg.feature_names_in_)
        print(f"feature_names_in_ ({len(feats)}): {feats}")
    else:
        print("No feature_names_in_ attribute")
        if hasattr(reg, 'n_features_in_'):
            print(f"n_features_in_: {reg.n_features_in_}")
    if hasattr(reg, 'steps'):
        print(f"Pipeline steps: {[s[0] for s in reg.steps]}")
    print()
except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
    print()

# ─── ANOMALY DETECTOR ──────────────────────────────────────────
print("=== anomaly_detector.joblib ===")
try:
    anom = joblib.load('anomaly_detector.joblib')
    print(f"Type: {type(anom).__name__}")
    print(f"Module: {type(anom).__module__}")
    if hasattr(anom, 'feature_names_in_'):
        feats = list(anom.feature_names_in_)
        print(f"feature_names_in_ ({len(feats)}): {feats}")
    else:
        print("No feature_names_in_ attribute")
        if hasattr(anom, 'n_features_in_'):
            print(f"n_features_in_: {anom.n_features_in_}")
    if hasattr(anom, 'steps'):
        print(f"Pipeline steps: {[s[0] for s in anom.steps]}")
    print()
except Exception as e:
    print(f"Error: {e}")
    import traceback; traceback.print_exc()
    print()

# ─── SCALERS ───────────────────────────────────────────────────
for fname in ['cls_scaler.joblib', 'reg_scaler.joblib']:
    print(f"=== {fname} ===")
    try:
        sc = joblib.load(fname)
        print(f"Type: {type(sc).__name__}")
        print(f"Module: {type(sc).__module__}")
        if hasattr(sc, 'feature_names_in_'):
            feats = list(sc.feature_names_in_)
            print(f"feature_names_in_ ({len(feats)}): {feats}")
        if hasattr(sc, 'n_features_in_'):
            print(f"n_features_in_: {sc.n_features_in_}")
        if hasattr(sc, 'mean_'):
            print(f"mean_ shape: {sc.mean_.shape}")
        if hasattr(sc, 'scale_'):
            print(f"scale_ shape: {sc.scale_.shape}")
        print()
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()
        print()

print("=== DONE ===")
sys.stdout.flush()
