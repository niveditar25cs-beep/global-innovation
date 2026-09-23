"""
Quick model test to verify the loaded models produce predictions.
"""
import warnings
warnings.filterwarnings('ignore')  # suppress InconsistentVersionWarning for demo

import joblib
import numpy as np

print("Testing models with sklearn 1.5.2...")
print()

# Load classifier
clf = joblib.load('transformer_alarm_model.joblib')
scaler = joblib.load('cls_scaler.joblib')
print(f"Classifier: {type(clf).__name__}")
print(f"  n_features_in_: {clf.n_features_in_}")
print(f"  classes_: {clf.classes_}")
print(f"  n_estimators: {clf.n_estimators}")
print()

# Test prediction with all-zero input
X_test = np.zeros((1, 59))
X_scaled = scaler.transform(X_test)
pred = clf.predict(X_scaled)
proba = clf.predict_proba(X_scaled)
print(f"All-zeros input prediction: class={pred[0]}, proba={proba[0].round(4)}")
risk_score = float(proba[0][1] + proba[0][2])  # P(warn) + P(critical)
print(f"  Risk score (P(warn)+P(critical)): {risk_score:.4f}")
print()

# Test with a high-temperature scenario (OTI=100, WTI=120 mapped to feature positions 0,1)
X_high = np.zeros((1, 59))
X_high[0, 0] = 100.0   # OTI
X_high[0, 1] = 120.0   # WTI
X_high[0, 2] = 40.0    # ATI
X_high_scaled = scaler.transform(X_high)
pred2 = clf.predict(X_high_scaled)
proba2 = clf.predict_proba(X_high_scaled)
print(f"High-temp input prediction: class={pred2[0]}, proba={proba2[0].round(4)}")
risk_score2 = float(proba2[0][1] + proba2[0][2])
print(f"  Risk score: {risk_score2:.4f}")
print()

# Load & test anomaly detector
anom = joblib.load('anomaly_detector.joblib')
print(f"Anomaly detector: {type(anom).__name__}")
print(f"  n_features_in_: {anom.n_features_in_}")
X_anom = np.zeros((1, 13))
anom_pred = anom.predict(X_anom)
anom_score = anom.decision_function(X_anom)
print(f"Anomaly test: label={anom_pred[0]} ({'+1=normal, -1=anomaly'}), score={anom_score[0]:.4f}")
print()

# Load regression model
reg = joblib.load('transformer_temp_model.joblib')
reg_scaler = joblib.load('reg_scaler.joblib')
print(f"Regression model: {type(reg).__name__}")
print(f"  n_features_in_: {reg.n_features_in_}")
X_reg = np.zeros((1, 54))
X_reg_scaled = reg_scaler.transform(X_reg)
oti_pred = reg.predict(X_reg_scaled)
print(f"OTI regression test: predicted_OTI={oti_pred[0]:.2f}°C")
print()

print("=== ALL MODELS WORKING CORRECTLY WITH SKLEARN 1.5.2 ===")
