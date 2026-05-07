"""JSON serialization utilities for numpy/pandas types."""

import math
import numpy as np
import pandas as pd


def safe(val):
    """Convert numpy/pandas types to JSON-serializable Python natives."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return 0
        return round(float(val), 2)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, pd.Timestamp):
        return str(val)
    if isinstance(val, str):
        return val
    if pd.isna(val):
        return None
    return val


def safe_str(val, default=""):
    """Return string or default for NaN."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    if pd.isna(val):
        return default
    return str(val)
