"""
Legacy Comparison Tests

Automated tests comparing new implementation with BatteryDataTool.py legacy code.
"""

import pytest
import sys
import os

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.validation.base_comparator import ComparisonConfig
from src.validation.toyo_cycle_comparator import ToyoCycleComparator
from src.utils.legacy_wrapper import check_battery_data_tool_available


# Check if BatteryDataTool.py is available
LEGACY_AVAILABLE = check_battery_data_tool_available()

pytestmark = pytest.mark.skipif(
    not LEGACY_AVAILABLE,
    reason="BatteryDataTool.py not found - legacy comparison tests require BatteryDataTool.py in parent directory"
)


class TestToyoCycleComparison:
    """Toyo Cycle Analyzer legacy comparison tests"""

    def test_cycle_comparison_auto_capacity(self):
        """Test cycle comparison with auto-capacity calculation"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,  # Auto-calculate
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Print detailed report
        comparator.print_report(result)

        # Assertions
        assert result.capacity_match, f"Capacity mismatch: legacy={result.capacity_legacy}, new={result.capacity_new}"
        assert result.passed, f"Comparison failed: {result.message}"
        assert result.within_tolerance == result.total_comparisons, "All rows should be within tolerance"
        assert result.mean_absolute_error < 0.1, f"Mean error too high: {result.mean_absolute_error}"

        print(f"\n[OK] Cycle comparison passed: {result.total_comparisons} cycles validated")

    def test_cycle_comparison_manual_capacity(self):
        """Test cycle comparison with manual capacity specification"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=2000.0,  # Manual specification
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Should use manual capacity
        assert result.capacity_legacy == 2000.0, "Legacy should use manual capacity"
        assert result.capacity_new == 2000.0, "New should use manual capacity"
        assert result.capacity_match, "Capacities should match"

        # Data comparison
        assert result.passed, f"Comparison failed: {result.message}"

        print(f"\n[OK] Manual capacity test passed")

    @pytest.mark.parametrize("path,channel", [
        ("Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc", "30"),
        ("Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc", "31"),
        ("Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc", "30"),
    ])
    def test_cycle_comparison_multiple_paths(self, path, channel):
        """Test cycle comparison across multiple Rawdata paths"""
        full_path = f"{path}/{channel}"

        # Check if path exists
        if not os.path.exists(full_path):
            pytest.skip(f"Path not found: {full_path}")

        config = ComparisonConfig(
            raw_file_path=full_path,
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Assertions
        assert result.capacity_match, f"Capacity mismatch for {full_path}"
        assert result.passed, f"Comparison failed for {full_path}: {result.message}"
        assert result.within_tolerance == result.total_comparisons, f"Tolerance issues for {full_path}"

        print(f"\n[OK] Path validation passed: {full_path}")

    def test_capacity_extraction_from_path(self):
        """Test automatic capacity extraction from path name"""
        # Path contains "1689mAh"
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,  # Auto-extract
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Capacity should be around 1689mAh
        assert 1600 <= result.capacity_legacy <= 1800, f"Unexpected capacity: {result.capacity_legacy}"
        assert 1600 <= result.capacity_new <= 1800, f"Unexpected capacity: {result.capacity_new}"
        assert result.capacity_match, "Capacities should match"

        print(f"\n[OK] Capacity extraction: {result.capacity_legacy} mAh")

    def test_column_wise_validation(self):
        """Test column-wise deviation validation"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Check each column has acceptable deviation
        expected_columns = ["Dchg", "Chg", "Eff", "Eff2", "DchgEng", "RndV", "AvgV", "Temp"]

        for col in expected_columns:
            assert col in result.column_deviations, f"Column {col} not found in deviations"

            stats = result.column_deviations[col]
            assert stats["match_percentage"] >= 95.0, f"Column {col} match rate too low: {stats['match_percentage']:.1f}%"
            assert stats["mean_abs_error"] < 1.0, f"Column {col} MAE too high: {stats['mean_abs_error']}"

        print(f"\n[OK] Column-wise validation passed for {len(expected_columns)} columns")

    def test_efficiency_calculation_accuracy(self):
        """Test efficiency calculation matches legacy"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Efficiency should have very low deviation
        eff_stats = result.column_deviations.get("Eff")
        assert eff_stats is not None, "Efficiency column not found"
        assert eff_stats["mean_abs_error"] < 0.01, f"Efficiency MAE too high: {eff_stats['mean_abs_error']}"
        assert eff_stats["max_deviation"] < 0.05, f"Efficiency max deviation too high: {eff_stats['max_deviation']}"

        print(f"\n[OK] Efficiency accuracy validated: MAE={eff_stats['mean_abs_error']:.6f}")

    @pytest.mark.slow
    def test_dcir_calculation(self):
        """Test DCIR calculation matches legacy (slow test - reads 100+ files)"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=True  # Enable DCIR
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # DCIR column should exist and match
        assert "dcir" in result.column_deviations, "DCIR column should be present when chkir=True"

        dcir_stats = result.column_deviations["dcir"]
        assert dcir_stats["match_percentage"] >= 90.0, f"DCIR match rate too low: {dcir_stats['match_percentage']:.1f}%"

        print(f"\n[OK] DCIR calculation validated: {dcir_stats['match_percentage']:.1f}% match")

    def test_nan_handling(self):
        """Test NaN handling in first/last cycles"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # First cycle often has NaN for charge capacity
        # Both implementations should handle NaN identically
        assert result.passed, f"NaN handling failed: {result.message}"

        print(f"\n[OK] NaN handling validated")

    def test_comparison_result_export(self):
        """Test comparison result can be exported to dict/JSON"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Export to dictionary
        result_dict = result.to_dict()

        # Validate structure
        assert "summary" in result_dict
        assert "capacity" in result_dict
        assert "column_deviations" in result_dict
        assert "mismatched_rows" in result_dict

        assert result_dict["summary"]["passed"] == result.passed
        assert result_dict["capacity"]["legacy"] == result.capacity_legacy
        assert result_dict["capacity"]["new"] == result.capacity_new

        print(f"\n[OK] Result export validated")


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s', '--tb=short'])
