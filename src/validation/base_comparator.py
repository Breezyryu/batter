"""
Base Legacy Comparator

Template Method Pattern for comparing legacy BatteryDataTool.py with new implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np


@dataclass
class ComparisonConfig:
    """Configuration for legacy comparison validation"""
    raw_file_path: str
    mincapacity: float = 0.0
    firstCrate: float = 0.2
    chkir: bool = False
    tolerances: Optional[Dict[str, float]] = None


@dataclass
class ComparisonResult:
    """Results of legacy vs new comparison"""
    # Summary metrics
    exact_matches: int
    within_tolerance: int
    total_comparisons: int
    max_deviation: float
    mean_absolute_error: float

    # Detailed metrics
    capacity_legacy: float
    capacity_new: float
    capacity_match: bool
    column_deviations: Dict[str, Dict[str, float]]
    mismatched_rows: List[int]

    # Overall result
    passed: bool
    message: str

    # Detailed comparison data
    details: pd.DataFrame = field(repr=False)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON export"""
        return {
            "summary": {
                "passed": self.passed,
                "message": self.message,
                "exact_matches": self.exact_matches,
                "within_tolerance": self.within_tolerance,
                "total_comparisons": self.total_comparisons,
                "match_percentage": f"{(self.within_tolerance / self.total_comparisons * 100):.2f}%",
                "max_deviation": self.max_deviation,
                "mean_absolute_error": self.mean_absolute_error
            },
            "capacity": {
                "legacy": self.capacity_legacy,
                "new": self.capacity_new,
                "match": self.capacity_match
            },
            "column_deviations": self.column_deviations,
            "mismatched_rows": self.mismatched_rows
        }


class BaseLegacyComparator(ABC):
    """
    Base class for legacy comparison using Template Method Pattern

    Compares legacy BatteryDataTool.py functions with new OOP implementation.
    """

    def __init__(self, config: ComparisonConfig):
        self.config = config
        self.tolerances = config.tolerances or self._default_tolerances()

    @abstractmethod
    def _run_legacy(self) -> Tuple[float, pd.DataFrame]:
        """
        Run legacy BatteryDataTool.py function

        Returns:
            Tuple of (mincapacity, result_dataframe)
        """
        pass

    @abstractmethod
    def _run_new(self) -> Tuple[float, pd.DataFrame]:
        """
        Run new OOP implementation

        Returns:
            Tuple of (mincapacity, result_dataframe)
        """
        pass

    @abstractmethod
    def _default_tolerances(self) -> Dict[str, float]:
        """
        Default tolerance values for comparison

        Returns:
            Dictionary mapping column names to tolerance values
        """
        pass

    @abstractmethod
    def _get_column_tolerance_map(self) -> Dict[str, str]:
        """
        Map DataFrame columns to tolerance keys

        Returns:
            Dictionary mapping column names to tolerance keys
        """
        pass

    def compare(self) -> ComparisonResult:
        """
        Main comparison pipeline

        Returns:
            ComparisonResult with detailed comparison metrics
        """
        # Step 1: Run both implementations
        try:
            legacy_cap, legacy_df = self._run_legacy()
            new_cap, new_df = self._run_new()
        except Exception as e:
            return ComparisonResult(
                exact_matches=0,
                within_tolerance=0,
                total_comparisons=0,
                max_deviation=0.0,
                mean_absolute_error=0.0,
                capacity_legacy=0.0,
                capacity_new=0.0,
                capacity_match=False,
                column_deviations={},
                mismatched_rows=[],
                passed=False,
                message=f"Execution error: {str(e)}",
                details=pd.DataFrame()
            )

        # Step 2: Compare capacity
        cap_tolerance = self.tolerances.get("capacity", 0.1)
        cap_match = abs(legacy_cap - new_cap) < cap_tolerance

        # Step 3: Compare DataFrames
        comparison_df, col_deviations, mismatched = self._compare_dataframes(legacy_df, new_df)

        # Step 4: Calculate metrics
        result = self._calculate_metrics(
            comparison_df, col_deviations, mismatched,
            legacy_cap, new_cap, cap_match
        )

        return result

    def _compare_dataframes(
        self,
        df1: pd.DataFrame,
        df2: pd.DataFrame
    ) -> Tuple[pd.DataFrame, Dict[str, Dict[str, float]], List[int]]:
        """
        Compare two DataFrames column by column

        Args:
            df1: Legacy DataFrame
            df2: New implementation DataFrame

        Returns:
            Tuple of (comparison_df, column_deviations, mismatched_rows)
        """
        # Ensure same shape
        if df1.shape != df2.shape:
            raise ValueError(f"DataFrame shape mismatch: {df1.shape} vs {df2.shape}")

        # Reset indexes for comparison
        df1_reset = df1.reset_index(drop=True)
        df2_reset = df2.reset_index(drop=True)

        # Get column tolerance mapping
        col_tolerance_map = self._get_column_tolerance_map()

        # Compare each column
        comparison_data = []
        col_deviations = {}
        mismatched_rows = []

        for idx in range(len(df1_reset)):
            row1 = df1_reset.iloc[idx]
            row2 = df2_reset.iloc[idx]

            row_comparison = {"row_index": idx, "match": True}
            row_mismatches = []

            for col in df1_reset.columns:
                if col not in df2_reset.columns:
                    continue

                val1 = row1[col]
                val2 = row2[col]

                # Handle NaN values
                if pd.isna(val1) and pd.isna(val2):
                    row_comparison[f"{col}_match"] = True
                    row_comparison[f"{col}_deviation"] = 0.0
                    continue
                elif pd.isna(val1) or pd.isna(val2):
                    row_comparison[f"{col}_match"] = False
                    row_comparison[f"{col}_deviation"] = float('inf')
                    row_mismatches.append(col)
                    continue

                # Calculate deviation
                deviation = abs(val1 - val2)
                tolerance_key = col_tolerance_map.get(col, "default")
                tolerance = self.tolerances.get(tolerance_key, 0.01)

                match = deviation <= tolerance

                row_comparison[f"{col}_match"] = match
                row_comparison[f"{col}_deviation"] = deviation

                if not match:
                    row_mismatches.append(col)
                    row_comparison["match"] = False

                # Track column-wise deviations
                if col not in col_deviations:
                    col_deviations[col] = {"deviations": [], "matches": 0, "total": 0}

                col_deviations[col]["deviations"].append(deviation)
                col_deviations[col]["total"] += 1
                if match:
                    col_deviations[col]["matches"] += 1

            comparison_data.append(row_comparison)

            if row_mismatches:
                mismatched_rows.append(idx)

        comparison_df = pd.DataFrame(comparison_data)

        # Calculate summary statistics for each column
        for col, stats in col_deviations.items():
            deviations = [d for d in stats["deviations"] if not np.isinf(d)]
            if deviations:
                stats["mean_abs_error"] = np.mean(deviations)
                stats["max_deviation"] = np.max(deviations)
                stats["match_percentage"] = (stats["matches"] / stats["total"]) * 100
            else:
                stats["mean_abs_error"] = 0.0
                stats["max_deviation"] = 0.0
                stats["match_percentage"] = 100.0

        return comparison_df, col_deviations, mismatched_rows

    def _calculate_metrics(
        self,
        comparison_df: pd.DataFrame,
        col_deviations: Dict[str, Dict[str, float]],
        mismatched_rows: List[int],
        legacy_cap: float,
        new_cap: float,
        cap_match: bool
    ) -> ComparisonResult:
        """
        Calculate comparison metrics

        Args:
            comparison_df: DataFrame with row-by-row comparison
            col_deviations: Column-wise deviation statistics
            mismatched_rows: List of row indices with mismatches
            legacy_cap: Legacy capacity value
            new_cap: New capacity value
            cap_match: Whether capacities match

        Returns:
            ComparisonResult with all metrics
        """
        total = len(comparison_df)
        exact_matches = comparison_df["match"].sum()
        within_tolerance = total - len(mismatched_rows)

        # Calculate overall MAE and max deviation
        all_deviations = []
        for col, stats in col_deviations.items():
            all_deviations.extend([d for d in stats["deviations"] if not np.isinf(d)])

        mae = np.mean(all_deviations) if all_deviations else 0.0
        max_dev = np.max(all_deviations) if all_deviations else 0.0

        # Determine pass/fail
        passed = cap_match and (within_tolerance == total)

        if passed:
            message = f"PASSED: All {total} rows within tolerance"
        elif not cap_match:
            message = f"FAILED: Capacity mismatch (legacy={legacy_cap:.2f}, new={new_cap:.2f})"
        else:
            message = f"FAILED: {len(mismatched_rows)} / {total} rows exceed tolerance"

        return ComparisonResult(
            exact_matches=exact_matches,
            within_tolerance=within_tolerance,
            total_comparisons=total,
            max_deviation=max_dev,
            mean_absolute_error=mae,
            capacity_legacy=legacy_cap,
            capacity_new=new_cap,
            capacity_match=cap_match,
            column_deviations=col_deviations,
            mismatched_rows=mismatched_rows,
            passed=passed,
            message=message,
            details=comparison_df
        )

    def print_report(self, result: ComparisonResult) -> None:
        """
        Print detailed comparison report

        Args:
            result: ComparisonResult to report
        """
        print("\n" + "=" * 70)
        print("=== Legacy Comparison Report ===")
        print("=" * 70)

        print(f"\nConfiguration:")
        print(f"  Path: {self.config.raw_file_path}")
        print(f"  MinCapacity: {'Auto-calculated' if self.config.mincapacity == 0 else self.config.mincapacity}")
        print(f"  FirstCrate: {self.config.firstCrate}")
        print(f"  CheckIR: {self.config.chkir}")

        print(f"\nCapacity Comparison:")
        print(f"  Legacy: {result.capacity_legacy:.1f} mAh")
        print(f"  New:    {result.capacity_new:.1f} mAh")
        print(f"  Match:  {'✓ (exact)' if abs(result.capacity_legacy - result.capacity_new) < 0.01 else '✓ (within tolerance)' if result.capacity_match else '✗'}")

        print(f"\nDataFrame Comparison:")
        print(f"  Total Rows:        {result.total_comparisons}")
        print(f"  Exact Matches:     {result.exact_matches} ({result.exact_matches / result.total_comparisons * 100:.1f}%)")
        print(f"  Within Tolerance:  {result.within_tolerance} ({result.within_tolerance / result.total_comparisons * 100:.1f}%)")
        print(f"  Max Deviation:     {result.max_deviation:.4f}")
        print(f"  Mean Abs Error:    {result.mean_absolute_error:.4f}")

        print(f"\nColumn-wise Deviations:")
        for col, stats in result.column_deviations.items():
            status = "✓" if stats["match_percentage"] == 100 else "~" if stats["match_percentage"] >= 95 else "✗"
            print(f"  {col:10s}: MAE={stats['mean_abs_error']:.4f}, Max={stats['max_deviation']:.4f}, "
                  f"Match={stats['match_percentage']:.1f}% {status}")

        print(f"\nResult: {'PASSED ✓' if result.passed else 'FAILED ✗'}")
        print(f"Message: {result.message}")

        if result.mismatched_rows:
            print(f"\nMismatched Rows (first 10): {result.mismatched_rows[:10]}")

        print("=" * 70 + "\n")
