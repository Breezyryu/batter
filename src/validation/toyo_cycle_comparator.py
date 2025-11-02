"""
Toyo Cycle Comparator

Compares legacy toyo_cycle_data() with ToyoCycleAnalyzer.
"""

from typing import Tuple, Dict
import pandas as pd

from src.validation.base_comparator import BaseLegacyComparator, ComparisonConfig
from src.core.toyo_cycle_analyzer import ToyoCycleAnalyzer
from src.utils.config_models import CycleConfig
from src.utils.legacy_wrapper import call_toyo_cycle_data


class ToyoCycleComparator(BaseLegacyComparator):
    """
    Compares Toyo Cycle data: legacy toyo_cycle_data() vs ToyoCycleAnalyzer

    Validates that new implementation produces identical results to legacy code.
    """

    def _run_legacy(self) -> Tuple[float, pd.DataFrame]:
        """
        Run legacy toyo_cycle_data() function

        Returns:
            Tuple of (mincapacity, result_dataframe)
        """
        capacity, df = call_toyo_cycle_data(
            raw_file_path=self.config.raw_file_path,
            mincapacity=self.config.mincapacity,
            inirate=self.config.firstCrate,
            chkir=self.config.chkir
        )

        return capacity, df

    def _run_new(self) -> Tuple[float, pd.DataFrame]:
        """
        Run new ToyoCycleAnalyzer implementation

        Returns:
            Tuple of (mincapacity, result_dataframe)
        """
        config = CycleConfig(
            raw_file_path=self.config.raw_file_path,
            mincapacity=self.config.mincapacity,
            firstCrate=self.config.firstCrate,
            chkir=self.config.chkir
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        return result.mincapacity, result.data

    def _default_tolerances(self) -> Dict[str, float]:
        """
        Default tolerance values for cycle data comparison

        Returns:
            Dictionary of tolerance values
        """
        return {
            "capacity": 0.1,      # ±0.1 for normalized capacity values
            "efficiency": 0.001,  # ±0.001 for ratio values (±0.1%)
            "voltage": 0.001,     # ±0.001 V (±1 mV)
            "energy": 0.1,        # ±0.1 mWh
            "temperature": 0.1,   # ±0.1 °C
            "dcir": 0.01,         # ±0.01 mΩ
            "default": 0.01       # Default for unmapped columns
        }

    def _get_column_tolerance_map(self) -> Dict[str, str]:
        """
        Map DataFrame columns to tolerance keys

        Returns:
            Dictionary mapping column names to tolerance keys
        """
        return {
            # Capacity columns (normalized)
            "Dchg": "capacity",
            "Chg": "capacity",

            # Efficiency columns (ratio 0-1)
            "Eff": "efficiency",
            "Eff2": "efficiency",

            # Voltage columns
            "RndV": "voltage",
            "AvgV": "voltage",

            # Energy column
            "DchgEng": "energy",

            # Temperature column
            "Temp": "temperature",

            # DCIR column
            "dcir": "dcir",

            # Original cycle number (should be exact match)
            "OriCyc": "default"
        }


def quick_compare(
    raw_file_path: str,
    mincapacity: float = 0.0,
    firstCrate: float = 0.2,
    chkir: bool = False,
    print_report: bool = True
):
    """
    Quick comparison helper function

    Args:
        raw_file_path: Path to Rawdata folder
        mincapacity: Specified capacity (0 for auto)
        firstCrate: Initial C-rate
        chkir: Calculate DCIR flag
        print_report: Print detailed report

    Returns:
        ComparisonResult object
    """
    config = ComparisonConfig(
        raw_file_path=raw_file_path,
        mincapacity=mincapacity,
        firstCrate=firstCrate,
        chkir=chkir
    )

    comparator = ToyoCycleComparator(config)
    result = comparator.compare()

    if print_report:
        comparator.print_report(result)

    return result
