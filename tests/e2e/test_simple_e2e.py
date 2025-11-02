"""
Simplified End-to-End Test

Tests complete workflow from raw data to legacy comparison.
"""

import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.validation.toyo_cycle_comparator import quick_compare
from src.utils.legacy_wrapper import check_battery_data_tool_available


class TestSimpleE2E:
    """
    Simplified end-to-end test using quick_compare()

    This validates the complete pipeline:
    1. Raw data loading (toyo_cycle_import)
    2. Cycle analysis (ToyoCycleAnalyzer)
    3. Legacy comparison (BatteryDataTool.py)
    4. Tolerance validation
    """

    @pytest.fixture
    def test_path(self):
        """Single test path for pipeline validation"""
        return "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

    def test_e2e_quick_comparison(self, test_path):
        """
        Complete end-to-end test using legacy comparison

        This single test validates:
        - Data loading from Rawdata path
        - Capacity calculation (auto-detect from path: 1689mAh)
        - Cycle analysis (all 100+ cycles)
        - Legacy compatibility (100% match with BatteryDataTool.py)
        - Column-wise validation (Dchg, Chg, Eff, Eff2, DchgEng, RndV, AvgV, Temp)
        """
        # Skip if test data not available
        if not os.path.exists(test_path):
            pytest.skip(f"Test path not found: {test_path}")

        # Skip if legacy code not available
        if not check_battery_data_tool_available():
            pytest.skip("BatteryDataTool.py not found - cannot perform legacy comparison")

        # Run complete pipeline with legacy comparison
        result = quick_compare(
            raw_file_path=test_path,
            mincapacity=0,  # Auto-calculate from path (1689mAh)
            firstCrate=0.2,
            chkir=False,
            print_report=True  # Print detailed comparison report
        )

        # ==========================================
        # Validation 1: Capacity Match
        # ==========================================
        assert result.capacity_match, \
            f"Capacity mismatch: legacy={result.capacity_legacy}, new={result.capacity_new}"

        # Expected capacity from path name: 1689mAh
        assert 1600 <= result.capacity_legacy <= 1800, \
            f"Unexpected capacity: {result.capacity_legacy}mAh (expected ≈1689mAh)"

        print(f"\n[OK] Capacity validation passed: {result.capacity_legacy}mAh")

        # ==========================================
        # Validation 2: Data Comparison
        # ==========================================
        assert result.passed, f"Comparison failed: {result.message}"
        assert result.within_tolerance == result.total_comparisons, \
            f"Not all rows within tolerance: {result.within_tolerance}/{result.total_comparisons}"

        print(f"[OK] Data comparison passed: {result.total_comparisons} cycles validated")

        # ==========================================
        # Validation 3: Error Metrics
        # ==========================================
        assert result.mean_absolute_error < 0.1, \
            f"Mean error too high: {result.mean_absolute_error:.6f} (target: <0.1)"

        assert result.max_deviation < 1.0, \
            f"Max deviation too high: {result.max_deviation:.6f} (target: <1.0)"

        print(f"[OK] Error metrics validated: MAE={result.mean_absolute_error:.6f}, MaxDev={result.max_deviation:.6f}")

        # ==========================================
        # Validation 4: Column-wise Accuracy
        # ==========================================
        expected_columns = ["Dchg", "Chg", "Eff", "Eff2", "DchgEng", "RndV", "AvgV", "Temp"]

        for col in expected_columns:
            assert col in result.column_deviations, f"Column {col} not found in results"

            stats = result.column_deviations[col]

            # Match percentage should be >95%
            assert stats["match_percentage"] >= 95.0, \
                f"Column {col} match rate too low: {stats['match_percentage']:.1f}% (target: ≥95%)"

            # Mean absolute error should be low
            assert stats["mean_abs_error"] < 1.0, \
                f"Column {col} MAE too high: {stats['mean_abs_error']:.6f} (target: <1.0)"

        print(f"[OK] Column-wise validation passed for {len(expected_columns)} columns")

        # ==========================================
        # Validation 5: Cycle Count
        # ==========================================
        assert result.total_comparisons > 90, \
            f"Expected ≈100 cycles, got {result.total_comparisons}"

        print(f"[OK] Cycle count validated: {result.total_comparisons} cycles")

        # ==========================================
        # Final Summary
        # ==========================================
        print(f"\n=== E2E Test Summary ===")
        print(f"✓ Capacity: {result.capacity_legacy}mAh (matches legacy)")
        print(f"✓ Cycles: {result.total_comparisons} (all within tolerance)")
        print(f"✓ MAE: {result.mean_absolute_error:.6f} (excellent accuracy)")
        print(f"✓ Match Rate: {(result.within_tolerance/result.total_comparisons)*100:.1f}%")
        print(f"✓ Columns: {len(expected_columns)} validated (all >95% match)")
        print(f"\n[OK] Complete E2E pipeline validated successfully!")

    @pytest.mark.parametrize("path,channel", [
        ("Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc", "30"),
        ("Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc", "31"),
        ("Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc", "30"),
    ])
    def test_e2e_multi_path(self, path, channel):
        """
        Test multiple Rawdata paths to ensure system works across different test periods

        Validates:
        - Different test periods (1-100cyc, 101-200cyc)
        - Different channels (30, 31)
        - Consistent behavior across all paths
        """
        full_path = f"{path}/{channel}"

        # Skip if test data not available
        if not os.path.exists(full_path):
            pytest.skip(f"Path not found: {full_path}")

        # Skip if legacy code not available
        if not check_battery_data_tool_available():
            pytest.skip("BatteryDataTool.py not found")

        # Run comparison
        result = quick_compare(
            raw_file_path=full_path,
            mincapacity=0,
            firstCrate=0.2,
            chkir=False,
            print_report=False  # Don't print detailed report for parametrized tests
        )

        # Validate results
        assert result.capacity_match, f"Capacity mismatch for {full_path}"
        assert result.passed, f"Comparison failed for {full_path}: {result.message}"
        assert result.within_tolerance == result.total_comparisons, \
            f"Tolerance issues for {full_path}"
        assert result.mean_absolute_error < 0.1, \
            f"MAE too high for {full_path}: {result.mean_absolute_error:.6f}"

        print(f"\n[OK] Path validated: {full_path} ({result.total_comparisons} cycles, MAE={result.mean_absolute_error:.6f})")


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s', '--tb=short'])
