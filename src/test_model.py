import pandas as pd
from predict import TransformerPredictor
import json

print("Loading trained Machine Learning models...")
predictor = TransformerPredictor(models_dir="./models")

print("Models loaded successfully!")
print("-" * 50)
print("Running a sample prediction...")

sample_data = {
    'VL1': 240.0, 'VL2': 239.5, 'VL3': 240.2,
    'IL1': 12.3, 'IL2': 11.8, 'IL3': 12.1,
    'OTI': 55.0, 'WTI': 60.0, 'ATI': 32.0, 'OLI': 45.0,
    'KW': 7.5, 'KVA': 8.2
}

result = predictor.predict_single(sample_data)

print("\nPrediction Result for the sample data:")
print(json.dumps(result, indent=2))
print("-" * 50)
