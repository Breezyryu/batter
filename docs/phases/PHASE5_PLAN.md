# Phase 5: Legacy Comparison & Validation System - Plan

## 📋 목표

새 시스템이 기존 BatteryDataTool.py와 100% 동일한 결과를 생성하는지 검증

## 🎯 Phase 5 Overview

### Core Components
1. **Legacy Wrapper**: BatteryDataTool.py 함수 호출 래퍼
2. **Comparison Engine**: 결과 비교 및 차이 분석
3. **Validation Framework**: Tolerance-based 검증
4. **Automated Test Suite**: 다양한 Rawdata 경로로 자동 검증
5. **Reporting**: 상세 비교 리포트 생성

## 🔍 Comparison Strategy

### 1. Cycle Data Comparison

**Source Functions**:
- **Legacy**: `toyo_cycle_data()` (BatteryDataTool.py line 636-751)
- **New**: `ToyoCycleAnalyzer.analyze()`

**Comparison Points**:
```python
# Output DataFrame columns (both should match)
columns = ["Dchg", "Chg", "Eff", "Eff2", "DchgEng", "RndV", "AvgV", "Temp", "OriCyc", "dcir"]

# Tolerance levels
tolerances = {
    "capacity": 0.1,      # ±0.1 mAh (normalized values)
    "efficiency": 0.001,  # ±0.1% (ratio values)
    "voltage": 0.001,     # ±1 mV
    "energy": 0.1,        # ±0.1 mWh
    "temperature": 0.1,   # ±0.1 °C
    "dcir": 0.01          # ±0.01 mΩ
}
```

**Validation Metrics**:
- **Exact Match Count**: Number of cycles with identical values
- **Within Tolerance**: Cycles within specified tolerance
- **Max Deviation**: Largest difference found
- **Mean Absolute Error**: Average difference across all cycles

### 2. Profile Data Comparison

**Source Functions**:
- **Legacy**: `toyo_rate_Profile_data()` (BatteryDataTool.py line 754-896)
- **New**: `ToyoRateProfileLoader.load_profile()`

**Comparison Points**:
```python
# Output DataFrame columns
columns = ["TimeMin", "SOC", "Vol", "Crate", "Temp"]

# Tolerance levels
tolerances = {
    "time": 0.01,        # ±0.01 minutes
    "soc": 0.001,        # ±0.1% SOC
    "voltage": 0.001,    # ±1 mV
    "crate": 0.001,      # ±0.001 C-rate
    "temperature": 0.1   # ±0.1 °C
}
```

### 3. Capacity Calculation Comparison

**Source Functions**:
- **Legacy**: `toyo_min_cap()` (BatteryDataTool.py line 516)
- **New**: Reused in `ToyoCycleAnalyzer._calculate_capacity()`

**Validation**:
- Direct comparison (should be identical, same function)
- Test with mincapacity=0 (auto-calculate)
- Test with manual mincapacity value

## 🏗️ Validation Framework Architecture

### Class Structure

```python
from dataclasses import dataclass
from typing import Dict, List, Tuple
import pandas as pd

@dataclass
class ComparisonConfig:
    """Configuration for comparison validation"""
    raw_file_path: str
    mincapacity: float = 0.0
    firstCrate: float = 0.2
    chkir: bool = False
    tolerances: Dict[str, float] = None

@dataclass
class ComparisonResult:
    """Results of legacy vs new comparison"""
    exact_matches: int
    within_tolerance: int
    total_comparisons: int
    max_deviation: float
    mean_absolute_error: float
    column_deviations: Dict[str, float]
    mismatched_rows: List[int]
    passed: bool
    details: pd.DataFrame

class BaseLegacyComparator(ABC):
    """Base class for legacy comparison"""

    def __init__(self, config: ComparisonConfig):
        self.config = config
        self.tolerances = config.tolerances or self._default_tolerances()

    @abstractmethod
    def _run_legacy(self) -> Tuple[float, pd.DataFrame]:
        """Run legacy BatteryDataTool.py function"""
        pass

    @abstractmethod
    def _run_new(self) -> Tuple[float, pd.DataFrame]:
        """Run new implementation"""
        pass

    @abstractmethod
    def _default_tolerances(self) -> Dict[str, float]:
        """Default tolerance values for comparison"""
        pass

    def compare(self) -> ComparisonResult:
        """Main comparison pipeline"""
        # 1. Run both implementations
        legacy_cap, legacy_df = self._run_legacy()
        new_cap, new_df = self._run_new()

        # 2. Compare capacity
        cap_match = abs(legacy_cap - new_cap) < self.tolerances.get("capacity", 0.1)

        # 3. Compare DataFrames
        comparison_df = self._compare_dataframes(legacy_df, new_df)

        # 4. Calculate metrics
        result = self._calculate_metrics(comparison_df, cap_match)

        return result

    def _compare_dataframes(self, df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
        """Compare two DataFrames column by column"""
        # Align indexes and columns
        # Calculate differences for each cell
        # Apply tolerances
        pass

    def _calculate_metrics(self, comparison_df: pd.DataFrame, cap_match: bool) -> ComparisonResult:
        """Calculate comparison metrics"""
        pass

class ToyoCycleComparator(BaseLegacyComparator):
    """Compares Toyo Cycle data: legacy vs new"""

    def _run_legacy(self) -> Tuple[float, pd.DataFrame]:
        """Call toyo_cycle_data() from BatteryDataTool.py"""
        # Import and call legacy function
        # Extract mincapacity and df.NewData
        pass

    def _run_new(self) -> Tuple[float, pd.DataFrame]:
        """Run ToyoCycleAnalyzer"""
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
        return {
            "capacity": 0.1,
            "efficiency": 0.001,
            "voltage": 0.001,
            "energy": 0.1,
            "temperature": 0.1,
            "dcir": 0.01
        }

class ToyoRateProfileComparator(BaseLegacyComparator):
    """Compares Toyo Rate Profile data: legacy vs new"""

    def _run_legacy(self) -> Tuple[float, pd.DataFrame]:
        """Call toyo_rate_Profile_data() from BatteryDataTool.py"""
        pass

    def _run_new(self) -> Tuple[float, pd.DataFrame]:
        """Run ToyoRateProfileLoader"""
        pass

    def _default_tolerances(self) -> Dict[str, float]:
        return {
            "time": 0.01,
            "soc": 0.001,
            "voltage": 0.001,
            "crate": 0.001,
            "temperature": 0.1
        }
```

## 📊 Reporting System

### Comparison Report Format

```
=== Legacy Comparison Report ===

Configuration:
  Path: Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30
  MinCapacity: Auto-calculated
  FirstCrate: 0.2
  CheckIR: False

Capacity Comparison:
  Legacy: 1689.0 mAh
  New:    1689.0 mAh
  Match:  ✓ (exact)

DataFrame Comparison:
  Rows:    103 cycles
  Columns: 9 (Dchg, Chg, Eff, Eff2, DchgEng, RndV, AvgV, Temp, OriCyc)

  Exact Matches:     98 / 103 (95.1%)
  Within Tolerance:  103 / 103 (100%)
  Max Deviation:     0.08 mAh (Dchg, cycle 45)
  Mean Abs Error:    0.02 mAh

Column-wise Deviations:
  Dchg:     MAE=0.02, Max=0.08 (within tolerance ✓)
  Chg:      MAE=0.01, Max=0.05 (within tolerance ✓)
  Eff:      MAE=0.0001, Max=0.0005 (within tolerance ✓)
  DchgEng:  MAE=0.05, Max=0.09 (within tolerance ✓)
  RndV:     MAE=0.0001, Max=0.0003 (within tolerance ✓)
  AvgV:     MAE=0.0001, Max=0.0002 (within tolerance ✓)
  Temp:     MAE=0.0, Max=0.0 (exact match ✓)

Result: PASSED ✓

Mismatched Rows (exceed tolerance): None
```

## 🧪 Automated Test Suite

### Test Cases

```python
# tests/validation/test_legacy_comparison.py

class TestLegacyComparison:
    """Automated legacy comparison tests"""

    @pytest.mark.parametrize("path,channel", [
        ("Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc", "30"),
        ("Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc", "30"),
        ("Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r", "10"),
    ])
    def test_toyo_cycle_comparison(self, path, channel):
        """Test Toyo cycle data comparison across multiple paths"""
        config = ComparisonConfig(
            raw_file_path=f"{path}/{channel}",
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        # Assertions
        assert result.passed, f"Comparison failed: {result.details}"
        assert result.within_tolerance == result.total_comparisons, "All rows should be within tolerance"
        assert result.mean_absolute_error < 0.1, "Mean error should be minimal"

    def test_capacity_auto_calculation(self):
        """Test auto-capacity calculation matches legacy"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,  # Auto-calculate
            firstCrate=0.2
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        assert result.passed, "Capacity calculation should match"

    def test_manual_capacity(self):
        """Test manual capacity specification"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=2000.0,  # Manual
            firstCrate=0.2
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        assert result.passed, "Manual capacity should work correctly"

    def test_dcir_calculation(self):
        """Test DCIR calculation matches legacy"""
        config = ComparisonConfig(
            raw_file_path="Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30",
            mincapacity=0,
            firstCrate=0.2,
            chkir=True  # Enable DCIR
        )

        comparator = ToyoCycleComparator(config)
        result = comparator.compare()

        assert result.passed, "DCIR calculation should match"
        assert "dcir" in result.column_deviations, "DCIR column should be compared"
```

## 📁 File Structure (Phase 5)

```
src/
├── validation/
│   ├── __init__.py                    # NEW: Package init
│   ├── base_comparator.py             # NEW: Base comparison class
│   ├── toyo_cycle_comparator.py       # NEW: Toyo cycle comparison
│   └── toyo_profile_comparator.py     # NEW: Toyo profile comparison
│
└── utils/
    └── legacy_wrapper.py              # NEW: BatteryDataTool.py wrapper

tests/
└── validation/
    ├── __init__.py                    # NEW
    ├── test_legacy_comparison.py      # NEW: Automated comparison tests
    └── test_comparison_framework.py   # NEW: Framework unit tests

docs/phases/
├── PHASE5_PLAN.md                     # NEW: This document
└── PHASE5_SUMMARY.md                  # To be created after completion
```

## 🎯 Implementation Steps

### Step 1: Legacy Wrapper
- [ ] Create `legacy_wrapper.py` to safely import and call BatteryDataTool.py functions
- [ ] Handle import path and dependencies
- [ ] Extract mincapacity and DataFrame from results

### Step 2: Base Comparison Framework
- [ ] Implement `BaseLegacyComparator` with Template Method Pattern
- [ ] Create `ComparisonConfig` and `ComparisonResult` models
- [ ] Implement DataFrame comparison logic with tolerance handling
- [ ] Calculate comparison metrics (exact matches, within tolerance, MAE, max deviation)

### Step 3: Cycle Comparator
- [ ] Implement `ToyoCycleComparator`
- [ ] Test with real Rawdata paths
- [ ] Verify capacity, efficiency, energy, voltage, temperature, DCIR

### Step 4: Profile Comparator
- [ ] Implement `ToyoRateProfileComparator`
- [ ] Test time-series data comparison
- [ ] Verify SOC, voltage, C-rate, temperature profiles

### Step 5: Automated Test Suite
- [ ] Create parametrized tests for multiple Rawdata paths
- [ ] Test auto-capacity vs manual capacity
- [ ] Test DCIR enabled vs disabled
- [ ] Test continuous paths (1-100cyc, 101-200cyc, etc.)

### Step 6: Reporting
- [ ] Implement detailed comparison report generator
- [ ] Create summary statistics
- [ ] Generate CSV/JSON export for results
- [ ] Create visualization for deviations (optional)

## 🔍 Key Design Decisions

### 1. Tolerance-Based Comparison
**Why**: Floating-point precision differences are expected
- DataFrame operations may produce slightly different rounding
- Tolerance levels based on measurement precision
- Separate tolerances for different physical quantities

### 2. Template Method Pattern (Again)
**Why**: Consistent with Phase 2 (Loader) and Phase 4 (Analyzer)
- `BaseLegacyComparator` defines comparison pipeline
- Vendor-specific comparators implement `_run_legacy()` and `_run_new()`
- Easy to extend for PNE comparisons

### 3. Legacy Function Reuse
**Why**: Phase 4 already reuses `toyo_min_cap()` and `toyo_cycle_import()`
- These functions are validated in Phase 4 tests
- Focus comparison on processing logic differences
- Capacity calculation should be identical (same function)

### 4. Parametrized Testing
**Why**: Test multiple Rawdata paths automatically
- Verify consistency across different battery tests
- Test edge cases (first cycle, last cycle, NaN handling)
- Continuous paths validation (101-200cyc follows 1-100cyc)

## 📊 Success Criteria

- ✅ Capacity calculation matches exactly (same function)
- ✅ All cycles within tolerance for capacity, efficiency, energy
- ✅ DataFrame shape matches (rows and columns)
- ✅ Automated tests pass for 3+ different Rawdata paths
- ✅ Mean Absolute Error < 0.1 for normalized values
- ✅ Comparison report clearly shows pass/fail status

## 📝 Notes

**Legacy Import Challenges**:
- BatteryDataTool.py is a standalone script, not a module
- May need to add `sys.path` manipulation
- Dependencies: numpy, pandas, matplotlib (already in requirements.txt)

**NaN Handling**:
- First cycle often missing charge data (NaN)
- Last cycle may have incomplete data
- Comparison should handle NaN values gracefully (`pd.notna()` checks)

**DCIR Calculation**:
- Requires reading individual cycle files (%06d format)
- Time-consuming operation (100+ file reads)
- Optional feature (chkir=False by default)

**Performance Consideration**:
- Legacy comparison adds overhead (2x computation)
- Use for validation, not production
- Cache comparison results for large test suites
