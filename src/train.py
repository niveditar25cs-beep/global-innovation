import os
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import (
    RandomForestClassifier, HistGradientBoostingClassifier,
    RandomForestRegressor, HistGradientBoostingRegressor, IsolationForest
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score
)

from data_loader import load_and_merge_data


def train_and_evaluate_models():
    os.makedirs("./models", exist_ok=True)
    os.makedirs("./reports", exist_ok=True)

    print("=" * 60)
    print("STEP 1: Loading and preprocessing transformer IoT data...")
    print("=" * 60)
    df = load_and_merge_data("./data")
    print(f"Total merged records: {len(df)} rows, {df.shape[1]} columns.\n")

    # -- Classification --
    exclude_cls = [
        'DeviceTimeStamp', 'OTI_A', 'OTI_T', 'MOG_A',
        'Fault_Risk_Level', 'Any_Alarm_Triggered'
    ]
    feature_cols_cls = [c for c in df.columns if c not in exclude_cls]

    y_cls = df['Fault_Risk_Level'].values
    X_cls = df[feature_cols_cls].values

    # Stratified split BEFORE any scaling (ML best practice)
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cls, y_cls, test_size=0.2, random_state=42, stratify=y_cls
    )

    scaler_cls = StandardScaler()
    X_train_c_s = scaler_cls.fit_transform(X_train_c)
    X_test_c_s = scaler_cls.transform(X_test_c)

    print("STEP 2: Training Classification Models (Fault Risk Level)")
    print("-" * 60)

    cls_models = {
        "LogisticRegression": LogisticRegression(max_iter=2000, random_state=42),
        "RandomForest": RandomForestClassifier(n_estimators=200, max_depth=14, random_state=42, n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingClassifier(max_iter=200, random_state=42),
    }

    # Which models need scaled data vs raw
    needs_scaling = {"LogisticRegression", "Ridge"}

    cls_results = {}
    best_cls_name = None
    best_cls_f1 = -1.0
    best_cls_model = None

    for name, model in cls_models.items():
        use_scaled = name in needs_scaling
        Xtr = X_train_c_s if use_scaled else X_train_c
        Xte = X_test_c_s if use_scaled else X_test_c

        model.fit(Xtr, y_train_c)
        train_preds = model.predict(Xtr)
        test_preds = model.predict(Xte)

        train_acc = accuracy_score(y_train_c, train_preds)
        test_acc = accuracy_score(y_test_c, test_preds)
        f1_macro = f1_score(y_test_c, test_preds, average='macro', zero_division=0)

        cls_results[name] = {
            "train_accuracy": round(float(train_acc), 4),
            "test_accuracy": round(float(test_acc), 4),
            "test_f1_macro": round(float(f1_macro), 4),
        }
        print(f"  {name:30s}  Train Acc={train_acc:.4f}  Test Acc={test_acc:.4f}  F1={f1_macro:.4f}")

        if f1_macro > best_cls_f1:
            best_cls_f1 = f1_macro
            best_cls_name = name
            best_cls_model = model

    print(f"\n>>> Best classifier: {best_cls_name} (F1 macro = {best_cls_f1:.4f})")

    # Confusion matrix for best model
    use_scaled = best_cls_name in needs_scaling
    Xte = X_test_c_s if use_scaled else X_test_c
    final_cls_preds = best_cls_model.predict(Xte)
    cm = confusion_matrix(y_test_c, final_cls_preds)

    plt.figure(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=['Normal', 'Warning', 'Critical'],
                yticklabels=['Normal', 'Warning', 'Critical'])
    plt.title(f'Confusion Matrix - {best_cls_name}')
    plt.ylabel('Actual'); plt.xlabel('Predicted')
    plt.tight_layout()
    plt.savefig('./reports/classification_confusion_matrix.png', dpi=200)
    plt.close()
    print("  Saved confusion matrix -> reports/classification_confusion_matrix.png")

    # Classification report text
    cls_report_text = classification_report(
        y_test_c, final_cls_preds,
        target_names=['Normal', 'Warning', 'Critical'], zero_division=0
    )
    with open('./reports/classification_report.txt', 'w') as f:
        f.write(cls_report_text)
    print("  Saved classification report -> reports/classification_report.txt\n")

    # -- Regression --
    print("STEP 3: Training Regression Models (Oil Temperature OTI)")
    print("-" * 60)

    exclude_reg = [
        'DeviceTimeStamp', 'OTI', 'WTI', 'OTI_A', 'OTI_T', 'MOG_A',
        'Fault_Risk_Level', 'Any_Alarm_Triggered',
        'OTI_ATI_Diff', 'WTI_ATI_Diff', 'WTI_OTI_Diff'
    ]
    feature_cols_reg = [c for c in df.columns if c not in exclude_reg]

    y_reg = df['OTI'].values
    X_reg = df[feature_cols_reg].values

    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42
    )

    scaler_reg = StandardScaler()
    X_train_r_s = scaler_reg.fit_transform(X_train_r)
    X_test_r_s = scaler_reg.transform(X_test_r)

    reg_models = {
        "Ridge": Ridge(alpha=1.0),
        "RandomForest": RandomForestRegressor(n_estimators=200, max_depth=14, random_state=42, n_jobs=-1),
        "HistGradientBoosting": HistGradientBoostingRegressor(max_iter=200, random_state=42),
    }

    reg_results = {}
    best_reg_name = None
    best_reg_r2 = -1e9
    best_reg_model = None

    for name, model in reg_models.items():
        use_scaled = name in needs_scaling
        Xtr = X_train_r_s if use_scaled else X_train_r
        Xte = X_test_r_s if use_scaled else X_test_r

        model.fit(Xtr, y_train_r)
        preds = model.predict(Xte)

        rmse = float(np.sqrt(mean_squared_error(y_test_r, preds)))
        mae  = float(mean_absolute_error(y_test_r, preds))
        r2   = float(r2_score(y_test_r, preds))

        reg_results[name] = {"test_rmse": round(rmse, 4), "test_mae": round(mae, 4), "test_r2": round(r2, 4)}
        print(f"  {name:30s}  RMSE={rmse:.4f}  MAE={mae:.4f}  R2={r2:.4f}")

        if r2 > best_reg_r2:
            best_reg_r2 = r2
            best_reg_name = name
            best_reg_model = model

    print(f"\n>>> Best regressor: {best_reg_name} (R2 = {best_reg_r2:.4f})")

    # Actual vs Predicted plot
    use_scaled = best_reg_name in needs_scaling
    Xte = X_test_r_s if use_scaled else X_test_r
    final_reg_preds = best_reg_model.predict(Xte)

    plt.figure(figsize=(7, 5))
    plt.scatter(y_test_r, final_reg_preds, alpha=0.25, s=8, color='#2563eb')
    lo = min(y_test_r.min(), final_reg_preds.min())
    hi = max(y_test_r.max(), final_reg_preds.max())
    plt.plot([lo, hi], [lo, hi], 'r--', lw=2, label='Ideal 1:1')
    plt.xlabel('Actual OTI (C)'); plt.ylabel('Predicted OTI (C)')
    plt.title(f'Actual vs Predicted Oil Temp - {best_reg_name}')
    plt.legend(); plt.tight_layout()
    plt.savefig('./reports/regression_actual_vs_pred.png', dpi=200)
    plt.close()
    print("  Saved regression plot -> reports/regression_actual_vs_pred.png\n")

    # -- Anomaly Detection --
    print("STEP 4: Training Isolation Forest (Anomaly Detection)")
    print("-" * 60)
    anomaly_features = [
        'VL1', 'VL2', 'VL3', 'IL1', 'IL2', 'IL3',
        'Voltage_Imbalance_Pct', 'Current_Imbalance_Pct',
        'Avg_THD_V', 'Avg_THD_I', 'Total_W', 'Total_VA', 'FRQ'
    ]
    X_anom = df[anomaly_features].values
    iso_forest = IsolationForest(n_estimators=150, contamination=0.05, random_state=42, n_jobs=-1)
    iso_forest.fit(X_anom)
    anomaly_labels = iso_forest.predict(X_anom)
    n_anomalies = (anomaly_labels == -1).sum()
    print(f"  Detected {n_anomalies} anomalies out of {len(anomaly_labels)} samples ({n_anomalies/len(anomaly_labels)*100:.2f}%)")
    joblib.dump(iso_forest, "./models/anomaly_detector.joblib")
    print("  Saved anomaly model -> models/anomaly_detector.joblib\n")

    # -- Serialize everything --
    print("STEP 5: Saving models and metadata...")
    print("-" * 60)
    joblib.dump(best_cls_model, "./models/transformer_alarm_model.joblib")
    joblib.dump(scaler_cls,     "./models/cls_scaler.joblib")
    joblib.dump(best_reg_model, "./models/transformer_temp_model.joblib")
    joblib.dump(scaler_reg,     "./models/reg_scaler.joblib")

    metadata = {
        "dataset": "Distributed Transformer Monitoring IoT Telemetry",
        "records": int(len(df)),
        "classification_target": "Fault_Risk_Level",
        "classification_features": feature_cols_cls,
        "best_classification_model": best_cls_name,
        "classification_results": cls_results,
        "regression_target": "OTI (Oil Temperature C)",
        "regression_features": feature_cols_reg,
        "best_regression_model": best_reg_name,
        "regression_results": reg_results,
        "anomaly_features": anomaly_features,
        "anomaly_contamination": 0.05,
        "classes": {"0": "Normal Operation", "1": "Warning / Pre-Alarm", "2": "Critical Alarm / Trip"},
    }
    with open("./models/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    with open("./reports/evaluation_summary.json", "w") as f:
        json.dump(metadata, f, indent=2)

    print("  All models and metadata saved to ./models/")
    print("=" * 60)
    print("TRAINING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    train_and_evaluate_models()
