import os
import pandas as pd
import numpy as np

def load_and_merge_data(data_dir="./data"):
    """
    Load all transformer CSV datasets, parse timestamps, merge on DeviceTimeStamp,
    and create rich engineered features for failure prediction and temperature forecasting.
    """
    alarm_path = os.path.join(data_dir, "Alarm.csv")
    cv_path = os.path.join(data_dir, "CurrentVoltage.csv")
    power_path = os.path.join(data_dir, "Power.csv")
    pf_path = os.path.join(data_dir, "PowerFactor.csv")
    tp_path = os.path.join(data_dir, "TotalPower.csv")

    df_alarm = pd.read_csv(alarm_path)
    df_cv = pd.read_csv(cv_path)
    df_power = pd.read_csv(power_path)
    df_pf = pd.read_csv(pf_path)
    df_tp = pd.read_csv(tp_path)

    # Standardize timestamp parsing
    for df in [df_alarm, df_cv, df_power, df_pf, df_tp]:
        df['DeviceTimeStamp'] = pd.to_datetime(df['DeviceTimeStamp'])
        df.sort_values('DeviceTimeStamp', inplace=True)

    # Merge on DeviceTimeStamp using outer join then sort
    merged_df = df_alarm.merge(df_cv, on='DeviceTimeStamp', how='outer')
    merged_df = merged_df.merge(df_power, on='DeviceTimeStamp', how='outer')
    merged_df = merged_df.merge(df_pf, on='DeviceTimeStamp', how='outer')
    merged_df = merged_df.merge(df_tp, on='DeviceTimeStamp', how='outer')

    merged_df.sort_values('DeviceTimeStamp', inplace=True)
    merged_df.reset_index(drop=True, inplace=True)

    # Time-based feature engineering
    merged_df['Hour'] = merged_df['DeviceTimeStamp'].dt.hour
    merged_df['DayOfWeek'] = merged_df['DeviceTimeStamp'].dt.dayofweek
    merged_df['Month'] = merged_df['DeviceTimeStamp'].dt.month

    # Imputation: Forward fill then backward fill for continuous IoT sensor streams
    sensor_cols = [c for c in merged_df.columns if c != 'DeviceTimeStamp']
    merged_df[sensor_cols] = merged_df[sensor_cols].ffill().bfill().fillna(0)

    # Domain Feature Engineering for Transformers
    # 1. Voltage Imbalance (%)
    v_mean = (merged_df['VL1'] + merged_df['VL2'] + merged_df['VL3']) / 3.0
    v_max_dev = np.maximum(
        np.abs(merged_df['VL1'] - v_mean),
        np.maximum(np.abs(merged_df['VL2'] - v_mean), np.abs(merged_df['VL3'] - v_mean))
    )
    merged_df['Voltage_Imbalance_Pct'] = np.where(v_mean > 10, (v_max_dev / v_mean) * 100, 0)

    # 2. Current Imbalance (%)
    i_mean = (merged_df['IL1'] + merged_df['IL2'] + merged_df['IL3']) / 3.0
    i_max_dev = np.maximum(
        np.abs(merged_df['IL1'] - i_mean),
        np.maximum(np.abs(merged_df['IL2'] - i_mean), np.abs(merged_df['IL3'] - i_mean))
    )
    merged_df['Current_Imbalance_Pct'] = np.where(i_mean > 1, (i_max_dev / i_mean) * 100, 0)

    # 3. Total Apparent Power & Total Reactive Power
    merged_df['Total_VA'] = merged_df['VAL1'] + merged_df['VAL2'] + merged_df['VAL3']
    merged_df['Total_W'] = merged_df['WL1'] + merged_df['WL2'] + merged_df['WL3']
    merged_df['Total_RVA'] = merged_df['RVAL1'] + merged_df['RVAL2'] + merged_df['RVAL3']

    # 4. Average Total Harmonic Distortion (THD)
    merged_df['Avg_THD_V'] = (merged_df['THDVL1'] + merged_df['THDVL2'] + merged_df['THDVL3']) / 3.0
    merged_df['Avg_THD_I'] = (merged_df['THDIL1'] + merged_df['THDIL2'] + merged_df['THDIL3']) / 3.0

    # 5. Temperature Rise over Ambient (Thermal Gradient)
    merged_df['OTI_ATI_Diff'] = merged_df['OTI'] - merged_df['ATI']
    merged_df['WTI_ATI_Diff'] = merged_df['WTI'] - merged_df['ATI']
    merged_df['WTI_OTI_Diff'] = merged_df['WTI'] - merged_df['OTI']

    # 6. Target 1: Alarm/Fault Risk Target
    # 0 = Normal, 1 = Warning / Pre-Alarm (High Temp or Low Oil or Gauge alert), 2 = Critical Alarm / Trip (OTI_A, OTI_T)
    has_trip = (merged_df['OTI_T'] > 0)
    has_alarm = (merged_df['OTI_A'] > 0)
    has_gauge_alarm = (merged_df['MOG_A'] > 0)
    high_temp_warning = (merged_df['OTI'] > 75) | (merged_df['WTI'] > 85) | (merged_df['OLI'] < 20)

    # Multi-class Target:
    # 0: Normal
    # 1: Warning
    # 2: Critical Alarm / Trip
    merged_df['Fault_Risk_Level'] = 0
    merged_df.loc[high_temp_warning | has_gauge_alarm, 'Fault_Risk_Level'] = 1
    merged_df.loc[has_alarm | has_trip, 'Fault_Risk_Level'] = 2

    # Binary Alarm Trigger target for direct alarm classification
    merged_df['Any_Alarm_Triggered'] = ((merged_df['OTI_A'] > 0) | (merged_df['OTI_T'] > 0) | (merged_df['MOG_A'] > 0)).astype(int)

    return merged_df

if __name__ == "__main__":
    df = load_and_merge_data()
    print(f"Merged Dataset Shape: {df.shape}")
    print("Class distribution for Fault_Risk_Level:")
    print(df['Fault_Risk_Level'].value_counts())
    print("\nClass distribution for Any_Alarm_Triggered:")
    print(df['Any_Alarm_Triggered'].value_counts())
