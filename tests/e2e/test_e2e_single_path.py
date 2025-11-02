"""
End-to-End Test: Single Path Complete Pipeline

Tests complete workflow from raw data files to database storage and queries.
"""

import pytest
import sys
import os
import tempfile
import pandas as pd
import time
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.toyo_loader import ToyoRateProfileLoader
from src.core.toyo_cycle_analyzer import ToyoCycleAnalyzer
from src.database.repository import TestProjectRepository, TestRunRepository, CycleDataRepository
from src.database.session import init_db, session_scope
from src.utils.config_models import ProfileConfig, CycleConfig
from src.validation.toyo_cycle_comparator import ToyoCycleComparator
from src.validation.base_comparator import ComparisonConfig


class TestE2ESinglePath:
    """
    End-to-end tests for single Rawdata path pipeline

    Tests the complete flow:
    Raw Files → Profile Loader → Cycle Analyzer → Repositories → Database → Queries
    """

    @pytest.fixture
    def test_path(self):
        """Single test path for pipeline validation"""
        return "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

    @pytest.fixture
    def test_db(self):
        """Create temporary database for E2E tests"""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        db_url = f"sqlite:///{db_path}"
        engine = init_db(db_url, echo=False)

        yield engine

        engine.dispose()
        if os.path.exists(db_path):
            os.unlink(db_path)

    def test_e2e_complete_pipeline(self, test_path, cleanup_database):
        """
        Test complete pipeline from raw files to database queries

        Pipeline Steps:
        1. Load profile metadata (info.txt)
        2. Analyze cycle data (capacity.log)
        3. Store in database (TestRun + Profile + CycleData)
        4. Query and validate results
        5. Compare with legacy implementation

        Expected Results:
        - Profile metadata matches info.txt
        - All cycles stored correctly (≈100 cycles)
        - Capacity calculation matches legacy (≈1689mAh)
        - Efficiency metrics match legacy (>99%)
        """
        # Check if test path exists
        if not os.path.exists(test_path):
            pytest.skip(f"Test path not found: {test_path}")

        # ==========================================
        # Step 1: Load Profile Metadata
        # ==========================================
        profile_config = ProfileConfig(raw_file_path=test_path)
        profile_loader = ToyoRateProfileLoader(profile_config)
        profile_result = profile_loader.load()

        assert profile_result.profile_data is not None, "Profile data should be loaded"
        assert profile_result.profile_data.capacity_mah > 0, "Capacity should be positive"

        print(f"\n[STEP 1] Profile loaded: {profile_result.profile_data.capacity_mah}mAh")

        # ==========================================
        # Step 2: Analyze Cycle Data
        # ==========================================
        cycle_config = CycleConfig(
            raw_file_path=test_path,
            mincapacity=0,  # Auto-calculate
            firstCrate=0.2,
            chkir=False
        )
        cycle_analyzer = ToyoCycleAnalyzer(cycle_config)
        cycle_result = cycle_analyzer.analyze()

        assert cycle_result.data is not None, "Cycle data should be analyzed"
        assert len(cycle_result.data) > 0, "Should have cycle data"
        assert cycle_result.mincapacity > 0, "Calculated capacity should be positive"

        print(f"[STEP 2] Cycles analyzed: {len(cycle_result.data)} cycles, capacity={cycle_result.mincapacity:.1f}mAh")

        # ==========================================
        # Step 3: Store in Database
        # ==========================================
        with session_scope() as session:
            # Create repositories
            test_run_repo = TestRunRepository(session)
            profile_repo = ProfileDataRepository(session)
            cycle_repo = CycleDataRepository(session)

            # Create test run
            test_run = test_run_repo.create(
                start_time=datetime.now(),
                raw_file_path=test_path
            )
            session.flush()
            test_run_id = test_run.id

            # Store profile
            profile_db = profile_repo.create(
                test_run_id=test_run_id,
                capacity_mah=profile_result.profile_data.capacity_mah,
                voltage_v=profile_result.profile_data.voltage_v,
                chemistry=profile_result.profile_data.chemistry,
                manufacturer=profile_result.profile_data.manufacturer
            )

            # Store cycles in batch
            cycle_records = []
            for idx, row in cycle_result.data.iterrows():
                cycle_data = {
                    "test_run_id": test_run_id,
                    "cycle_number": int(row["OriCyc"]),
                    "discharge_capacity": float(row["Dchg"]) if not cycle_result.data["Dchg"].isna().iloc[idx] else None,
                    "charge_capacity": float(row["Chg"]) if not cycle_result.data["Chg"].isna().iloc[idx] else None,
                    "coulombic_efficiency": float(row["Eff"]) if not cycle_result.data["Eff"].isna().iloc[idx] else None,
                    "energy_efficiency": float(row["Eff2"]) if not cycle_result.data["Eff2"].isna().iloc[idx] else None,
                    "discharge_energy": float(row["DchgEng"]) if not cycle_result.data["DchgEng"].isna().iloc[idx] else None,
                    "round_trip_voltage": float(row["RndV"]) if not cycle_result.data["RndV"].isna().iloc[idx] else None,
                    "average_voltage": float(row["AvgV"]) if not cycle_result.data["AvgV"].isna().iloc[idx] else None,
                    "temperature": float(row["Temp"]) if not cycle_result.data["Temp"].isna().iloc[idx] else None
                }
                cycle_records.append(cycle_data)

            cycles_db = cycle_repo.create_batch(cycle_records)
            session.flush()

        print(f"[STEP 3] Database stored: TestRun={test_run_id}, Profile={profile_db.id}, Cycles={len(cycles_db)}")

        # ==========================================
        # Step 4: Query and Validate Results
        # ==========================================
        with session_scope() as session:
            test_run_repo = TestRunRepository(session)
            profile_repo = ProfileDataRepository(session)
            cycle_repo = CycleDataRepository(session)

            # Query test run
            queried_test_run = test_run_repo.get_by_id(test_run_id)
            assert queried_test_run is not None, "Test run should be queryable"
            assert queried_test_run.raw_file_path == test_path

            # Query profile
            queried_profile = profile_repo.get_by_test_run(test_run_id)
            assert queried_profile is not None, "Profile should be queryable"
            assert abs(queried_profile.capacity_mah - profile_result.profile_data.capacity_mah) < 0.1

            # Query cycles
            queried_cycles = cycle_repo.get_by_test_run(test_run_id)
            assert len(queried_cycles) == len(cycle_result.data), "All cycles should be queryable"

            # Validate cycle data integrity
            first_cycle = queried_cycles[0]
            assert first_cycle.test_run_id == test_run_id
            assert first_cycle.cycle_number > 0

        print(f"[STEP 4] Database queries validated: {len(queried_cycles)} cycles retrieved")

        # ==========================================
        # Step 5: Compare with Legacy Implementation
        # ==========================================
        from src.utils.legacy_wrapper import check_battery_data_tool_available

        if check_battery_data_tool_available():
            comparison_config = ComparisonConfig(
                raw_file_path=test_path,
                mincapacity=0,
                firstCrate=0.2,
                chkir=False
            )
            comparator = ToyoCycleComparator(comparison_config)
            comparison_result = comparator.compare()

            # Validate capacity match
            assert comparison_result.capacity_match, \
                f"Capacity mismatch: legacy={comparison_result.capacity_legacy}, new={comparison_result.capacity_new}"

            # Validate data match
            assert comparison_result.passed, f"Comparison failed: {comparison_result.message}"
            assert comparison_result.within_tolerance == comparison_result.total_comparisons, \
                "All rows should be within tolerance"

            # Validate efficiency
            assert comparison_result.mean_absolute_error < 0.1, \
                f"Mean error too high: {comparison_result.mean_absolute_error}"

            print(f"[STEP 5] Legacy validation passed: {comparison_result.total_comparisons} cycles, MAE={comparison_result.mean_absolute_error:.6f}")
        else:
            print("[STEP 5] Legacy validation skipped (BatteryDataTool.py not available)")

        # ==========================================
        # Final Assertions
        # ==========================================
        assert len(cycle_result.data) > 90, f"Expected ≈100 cycles, got {len(cycle_result.data)}"
        assert 1600 <= cycle_result.mincapacity <= 1800, \
            f"Expected capacity ≈1689mAh, got {cycle_result.mincapacity}mAh"

        # Validate efficiency
        avg_efficiency = cycle_result.data["Eff"].mean()
        assert avg_efficiency > 0.98, f"Expected efficiency >98%, got {avg_efficiency*100:.2f}%"

        print(f"\n[OK] E2E pipeline test passed")
        print(f"  - Cycles: {len(cycle_result.data)}")
        print(f"  - Capacity: {cycle_result.mincapacity:.1f}mAh")
        print(f"  - Efficiency: {avg_efficiency*100:.2f}%")
        print(f"  - Database: TestRun + Profile + {len(cycles_db)} CycleData records")

    def test_e2e_performance_baseline(self, test_path, cleanup_database):
        """
        Establish performance baseline for single path processing

        Performance Targets:
        - Analysis: <1s for 100 cycles (10ms/cycle)
        - Database insert: <10ms for 100 cycles (0.1ms/cycle)
        - Database query: <100ms for 100 cycles
        """
        import time

        if not os.path.exists(test_path):
            pytest.skip(f"Test path not found: {test_path}")

        # ==========================================
        # Benchmark 1: Profile Loading
        # ==========================================
        profile_config = ProfileConfig(raw_file_path=test_path)
        profile_loader = ToyoRateProfileLoader(profile_config)

        start_time = time.time()
        profile_result = profile_loader.load()
        profile_time = time.time() - start_time

        print(f"\n[BENCHMARK] Profile loading: {profile_time*1000:.2f}ms")

        # ==========================================
        # Benchmark 2: Cycle Analysis
        # ==========================================
        cycle_config = CycleConfig(
            raw_file_path=test_path,
            mincapacity=0,
            firstCrate=0.2,
            chkir=False
        )
        cycle_analyzer = ToyoCycleAnalyzer(cycle_config)

        start_time = time.time()
        cycle_result = cycle_analyzer.analyze()
        analysis_time = time.time() - start_time

        cycle_count = len(cycle_result.data)
        time_per_cycle = (analysis_time / cycle_count) * 1000  # ms per cycle

        print(f"[BENCHMARK] Cycle analysis: {analysis_time*1000:.2f}ms for {cycle_count} cycles ({time_per_cycle:.2f}ms/cycle)")

        # Target: <10ms per cycle
        assert time_per_cycle < 10, f"Analysis too slow: {time_per_cycle:.2f}ms/cycle (target: <10ms/cycle)"

        # ==========================================
        # Benchmark 3: Database Insert
        # ==========================================
        with session_scope() as session:
            test_run_repo = TestRunRepository(session)
            profile_repo = ProfileDataRepository(session)
            cycle_repo = CycleDataRepository(session)

            # Create test run
            test_run = test_run_repo.create(
                start_time=datetime.now(),
                raw_file_path=test_path
            )
            session.flush()
            test_run_id = test_run.id

            # Store profile
            profile_repo.create(
                test_run_id=test_run_id,
                capacity_mah=profile_result.profile_data.capacity_mah,
                voltage_v=profile_result.profile_data.voltage_v,
                chemistry=profile_result.profile_data.chemistry,
                manufacturer=profile_result.profile_data.manufacturer
            )

            # Benchmark batch insert
            cycle_records = []
            for idx, row in cycle_result.data.iterrows():
                cycle_data = {
                    "test_run_id": test_run_id,
                    "cycle_number": int(row["OriCyc"]),
                    "discharge_capacity": float(row["Dchg"]) if not cycle_result.data["Dchg"].isna().iloc[idx] else None,
                    "charge_capacity": float(row["Chg"]) if not cycle_result.data["Chg"].isna().iloc[idx] else None,
                    "coulombic_efficiency": float(row["Eff"]) if not cycle_result.data["Eff"].isna().iloc[idx] else None
                }
                cycle_records.append(cycle_data)

            start_time = time.time()
            cycle_repo.create_batch(cycle_records)
            session.flush()
            insert_time = time.time() - start_time

        insert_time_per_cycle = (insert_time / cycle_count) * 1000  # ms per cycle

        print(f"[BENCHMARK] Database insert: {insert_time*1000:.2f}ms for {cycle_count} cycles ({insert_time_per_cycle:.3f}ms/cycle)")

        # Target: <0.1ms per cycle
        assert insert_time_per_cycle < 0.1, f"Insert too slow: {insert_time_per_cycle:.3f}ms/cycle (target: <0.1ms/cycle)"

        # ==========================================
        # Benchmark 4: Database Query
        # ==========================================
        with session_scope() as session:
            cycle_repo = CycleDataRepository(session)

            start_time = time.time()
            queried_cycles = cycle_repo.get_by_test_run(test_run_id)
            query_time = time.time() - start_time

        print(f"[BENCHMARK] Database query: {query_time*1000:.2f}ms for {len(queried_cycles)} cycles")

        # Target: <100ms for 100 cycles
        assert query_time < 0.1, f"Query too slow: {query_time*1000:.2f}ms (target: <100ms)"

        # ==========================================
        # Summary
        # ==========================================
        total_time = profile_time + analysis_time + insert_time + query_time

        print(f"\n[OK] Performance baseline established:")
        print(f"  - Profile loading: {profile_time*1000:.2f}ms")
        print(f"  - Cycle analysis: {analysis_time*1000:.2f}ms ({time_per_cycle:.2f}ms/cycle)")
        print(f"  - Database insert: {insert_time*1000:.2f}ms ({insert_time_per_cycle:.3f}ms/cycle)")
        print(f"  - Database query: {query_time*1000:.2f}ms")
        print(f"  - Total pipeline: {total_time*1000:.2f}ms")

        # All benchmarks should pass
        assert total_time < 2.0, f"Total pipeline too slow: {total_time:.2f}s (target: <2s)"


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '-s', '--tb=short'])
