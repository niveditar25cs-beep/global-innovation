"""
Try to determine the sklearn version the models were trained with
by reading the raw pickle bytes.
"""
import struct
import sys

def peek_joblib_sklearn_version(filepath):
    """Read raw bytes to find sklearn version string in pickle."""
    try:
        with open(filepath, 'rb') as f:
            data = f.read(min(50000, 200000))  # read first 50KB
        
        # Search for 'sklearn' version markers
        text = data.decode('latin1', errors='replace')
        
        # Look for version strings
        import re
        # joblib stores numpy version, sklearn might be in __getstate__
        vers = re.findall(r'sklearn[^\'\"\\x00]{0,5}[\'\"]?[\s]*:?\s*[\'\"]?([\d]+\.[\d]+\.[\d]+)', text)
        vers2 = re.findall(r'__sklearn_version__[^0-9]{0,10}([\d]+\.[\d]+\.[\d]+)', text)
        vers3 = re.findall(r'([\d]+\.[\d]+\.[\d]+)[\x00]{0,5}sklearn', text)
        
        print(f"Version matches found:")
        print(f"  Pattern 1: {vers}")
        print(f"  Pattern 2: {vers2}")  
        print(f"  Pattern 3: {vers3}")
        
        # Look for the version in the bytes directly
        for v_pattern in [b'1.0.', b'1.1.', b'1.2.', b'1.3.', b'1.4.', b'1.5.', b'0.24', b'0.23']:
            if v_pattern in data:
                idx = data.find(v_pattern)
                snippet = data[max(0,idx-30):idx+15].decode('latin1', errors='replace')
                print(f"  Found {v_pattern}: ...{repr(snippet)}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback; traceback.print_exc()

print("=== cls_scaler.joblib (loads successfully - check version) ===")
peek_joblib_sklearn_version('cls_scaler.joblib')
print()
print("=== transformer_alarm_model.joblib ===")
peek_joblib_sklearn_version('transformer_alarm_model.joblib')
print()

# Also check what exact error is - the DLL name gives us info
print("=== DLL blocking analysis ===")
print("'_middle_term_computer' is NOT a standard sklearn module name.")
print("This suggests the models may have been trained with a patched/custom sklearn.")
print("OR the error message may be misleading - let's try a direct import test.")

try:
    import sklearn.ensemble
    print("sklearn.ensemble: OK")
except Exception as e:
    print(f"sklearn.ensemble FAILED: {e}")

try:
    import sklearn.ensemble._forest
    print("sklearn.ensemble._forest: OK")
except Exception as e:
    print(f"sklearn.ensemble._forest FAILED: {e}")

try:
    import sklearn.ensemble._gb
    print("sklearn.ensemble._gb: OK")
except Exception as e:
    print(f"sklearn.ensemble._gb FAILED: {e}")

sys.stdout.flush()
