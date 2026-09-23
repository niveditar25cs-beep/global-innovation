import os
import json
import joblib
import numpy as np
import pandas as pd

class TransformerPredictor:
    def __init__(self, models_dir="./models"):
        self.models_dir = models_dir
        self.cls_model = joblib.load(os.path.join(models_dir, "transformer_alarm_model.joblib"))
        self.cls_scaler = joblib.load(os.path.join(models_dir, "cls_scaler.joblib"))
        self.reg_model = joblib.load(os.path.join(models_dir, "transformer_temp_model.joblib"))
        self.reg_scaler = joblib.load(os.path.join(models_dir, "reg_scaler.joblib"))
        
        with open(os.path.join(models_dir, "metadata.json"), "r") as f:
            self.metadata = json.load(f)

        self.cls_features = self.metadata["classification_features"]
        self.reg_features = self.metadata["regression_features"]
        self.classes = {int(k): v for k, v in self.metadata["classes"].items()}

    def _engineer_features(self, df_input):
        df = df_input.copy()
        
        # Ensure timestamp if present
        if 'DeviceTimeStamp' in df.columns:
            df['DeviceTimeStamp'] = pd.to_datetime(df['DeviceTimeStamp'])
            df['Hour'] = df['DeviceTimeStamp'].dt.hour
            df['DayOfWeek'] = df['DeviceTimeStamp'].dt.dayofweek
            df['Month'] = df['DeviceTimeStamp'].dt.month
        else:
            if 'Hour' not in df.columns: df['Hour'] = 12
            if 'DayOfWeek' not in df.columns: df['DayOfWeek'] = 2
            if 'Month' not in df.columns: df['Month'] = 6

        # Fill missing default columns if needed
        all_needed = set(self.cls_features + self.reg_features)
        for col in all_needed:
            if col not in df.columns:
                df[col] = 0.0

        # Calculations
        v_mean = (df['VL1'] + df['VL2'] + df['VL3']) / 3.0
        v_max_dev = np.maximum(
            np.abs(df['VL1'] - v_mean),
            np.maximum(np.abs(df['VL2'] - v_mean), np.abs(df['VL3'] - v_mean))
        )
        df['Voltage_Imbalance_Pct'] = np.where(v_mean > 10, (v_max_dev / v_mean) * 100, 0)

        i_mean = (df['IL1'] + df['IL2'] + df['IL3']) / 3.0
        i_max_dev = np.maximum(
            np.abs(df['IL1'] - i_mean),
            np.maximum(np.abs(df['IL2'] - i_mean), np.abs(df['IL3'] - i_mean))
        )
        df['Current_Imbalance_Pct'] = np.where(i_mean > 1, (i_max_dev / i_mean) * 100, 0)

        df['Total_VA'] = df['VAL1'] + df['VAL2'] + df['VAL3']
        df['Total_W'] = df['WL1'] + df['WL2'] + df['WL3']
        df['Total_RVA'] = df['RVAL1'] + df['RVAL2'] + df['RVAL3']

        df['Avg_THD_V'] = (df['THDVL1'] + df['THDVL2'] + df['THDVL3']) / 3.0
        df['Avg_THD_I'] = (df['THDIL1'] + df['THDIL2'] + df['THDIL3']) / 3.0

        if 'OTI' in df.columns and 'ATI' in df.columns:
            df['OTI_ATI_Diff'] = df['OTI'] - df['ATI']
        if 'WTI' in df.columns and 'ATI' in df.columns:
            df['WTI_ATI_Diff'] = df['WTI'] - df['ATI']
        if 'WTI' in df.columns and 'OTI' in df.columns:
            df['WTI_OTI_Diff'] = df['WTI'] - df['OTI']

        return df

    def predict_single(self, input_dict):
        """
        Takes dictionary of sensor features and returns risk level, probabilities, and predicted temperature.
        """
        df = pd.DataFrame([input_dict])
        df_feats = self._engineer_features(df)

        X_c = df_feats[self.cls_features].values
        X_r = df_feats[self.reg_features].values

        # Classification inference
        if hasattr(self.cls_model, "predict_proba"):
            probs = self.cls_model.predict_proba(X_c)[0].tolist()
        else:
            probs = [0.0, 0.0, 0.0]
        
        pred_class = int(self.cls_model.predict(X_c)[0])
        pred_label = self.classes.get(pred_class, "Unknown")

        # Regression inference (predicted OTI)
        pred_oti = float(self.reg_model.predict(X_r)[0])

        return {
            "predicted_risk_level": pred_class,
            "risk_label": pred_label,
            "probabilities": {
                "Normal": round(probs[0], 4) if len(probs) > 0 else 0,
                "Warning": round(probs[1], 4) if len(probs) > 1 else 0,
                "Critical_Alarm": round(probs[2], 4) if len(probs) > 2 else 0
            },
            "predicted_oil_temperature_celsius": round(pred_oti, 2),
            "safety_status": "CRITICAL" if pred_class == 2 else ("WARNING" if pred_class == 1 else "OPTIMAL")
        }

    def predict_batch(self, df_input):
        df_feats = self._engineer_features(df_input)
        X_c = df_feats[self.cls_features].values
        X_r = df_feats[self.reg_features].values

        preds_c = self.cls_model.predict(X_c)
        preds_r = self.reg_model.predict(X_r)

        result_df = df_input.copy()
        result_df['Predicted_Fault_Risk'] = preds_c
        result_df['Risk_Status'] = [self.classes.get(c, "Unknown") for c in preds_c]
        result_df['Predicted_OTI_Temp_C'] = np.round(preds_r, 2)
        return result_df
