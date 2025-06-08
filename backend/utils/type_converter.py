from typing import Any, Dict, List, Union
import numpy as np

def convert_numpy_types(obj: Any) -> Union[Dict, List, str, int, float, bool, None]:
    """
    Recursively convert NumPy types to native Python types.
    
    Args:
        obj: Any Python or NumPy object
        
    Returns:
        The same object with all NumPy types converted to native Python types
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()  # Converts any NumPy type to its native Python equivalent
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert NumPy arrays to Python lists
    return obj 