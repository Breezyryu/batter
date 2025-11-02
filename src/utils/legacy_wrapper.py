"""
Legacy Wrapper for BatteryDataTool.py Functions

Provides safe interface to call legacy BatteryDataTool.py functions for validation.
"""

import sys
import os
from typing import Tuple
import pandas as pd


def import_battery_data_tool():
    """
    Import BatteryDataTool.py module

    Returns:
        Module object for BatteryDataTool

    Raises:
        ImportError: If BatteryDataTool.py not found
    """
    # Get the parent directory (should contain BatteryDataTool.py)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    parent_dir = os.path.dirname(project_root)

    # Add parent directory to path if not already there
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)

    try:
        import BatteryDataTool
        return BatteryDataTool
    except ImportError as e:
        raise ImportError(
            f"Could not import BatteryDataTool.py. "
            f"Make sure it exists in the parent directory: {parent_dir}\n"
            f"Error: {str(e)}"
        )


def call_toyo_cycle_data(
    raw_file_path: str,
    mincapacity: float = 0.0,
    inirate: float = 0.2,
    chkir: bool = False
) -> Tuple[float, pd.DataFrame]:
    """
    Call legacy toyo_cycle_data() function

    Args:
        raw_file_path: Path to Rawdata folder
        mincapacity: Specified capacity (0 for auto-calculate)
        inirate: Initial C-rate (default 0.2)
        chkir: Calculate DCIR flag

    Returns:
        Tuple of (mincapacity, result_dataframe)

    Raises:
        ImportError: If BatteryDataTool.py not found
        Exception: If legacy function fails
    """
    BDT = import_battery_data_tool()

    # Call legacy function
    result = BDT.toyo_cycle_data(raw_file_path, mincapacity, inirate, chkir)

    # Extract capacity and DataFrame
    if isinstance(result, list) and len(result) >= 2:
        capacity = result[0]
        df_wrapper = result[1]

        # Extract DataFrame from wrapper object
        if hasattr(df_wrapper, 'NewData'):
            df = df_wrapper.NewData
        else:
            raise ValueError("Legacy result does not have 'NewData' attribute")

        return capacity, df
    else:
        raise ValueError(f"Unexpected legacy result format: {type(result)}")


def call_toyo_rate_profile_data(
    raw_file_path: str,
    inicycle: int,
    mincapacity: float = 0.0,
    cutoff: float = 0.05,
    inirate: float = 0.2,
    smoothdegree: int = 0
) -> Tuple[float, pd.DataFrame]:
    """
    Call legacy toyo_rate_Profile_data() function

    Args:
        raw_file_path: Path to Rawdata folder with cycle number
        inicycle: Cycle number to analyze
        mincapacity: Specified capacity (0 for auto-calculate)
        cutoff: Cutoff SOC value
        inirate: Initial C-rate
        smoothdegree: Smoothing degree

    Returns:
        Tuple of (mincapacity, result_dataframe)

    Raises:
        ImportError: If BatteryDataTool.py not found
        Exception: If legacy function fails
    """
    BDT = import_battery_data_tool()

    # Call legacy function
    result = BDT.toyo_rate_Profile_data(
        raw_file_path, inicycle, mincapacity, cutoff, inirate, smoothdegree
    )

    # Extract capacity and DataFrame
    if isinstance(result, list) and len(result) >= 2:
        capacity = result[0]
        df_wrapper = result[1]

        # Extract DataFrame from wrapper object
        if hasattr(df_wrapper, 'NewData'):
            df = df_wrapper.NewData
        else:
            raise ValueError("Legacy result does not have 'NewData' attribute")

        return capacity, df
    else:
        raise ValueError(f"Unexpected legacy result format: {type(result)}")


def call_toyo_min_cap(
    raw_file_path: str,
    mincapacity: float = 0.0,
    inirate: float = 0.2
) -> float:
    """
    Call legacy toyo_min_cap() function

    Args:
        raw_file_path: Path to Rawdata folder
        mincapacity: Specified capacity (0 for auto-calculate)
        inirate: Initial C-rate

    Returns:
        Calculated or specified capacity

    Raises:
        ImportError: If BatteryDataTool.py not found
    """
    BDT = import_battery_data_tool()
    return BDT.toyo_min_cap(raw_file_path, mincapacity, inirate)


def check_battery_data_tool_available() -> bool:
    """
    Check if BatteryDataTool.py is available

    Returns:
        True if BatteryDataTool.py can be imported, False otherwise
    """
    try:
        import_battery_data_tool()
        return True
    except ImportError:
        return False
