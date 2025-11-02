"""
Cycle Analyzer → Database Integration Tests

Complete pipeline validation: Analyzer → Repository → DB → Query
"""

import pytest
import sys
import os
import tempfile
import pandas as pd

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.toyo_cycle_analyzer import ToyoCycleAnalyzer
from src.utils.config_models import CycleConfig
from src.database.models import TestProject, TestRun, CycleData
from src.database.session import init_db, session_scope
from src.database.repository import (
    TestProjectRepository,
    TestRunRepository,
    CycleDataRepository
)


@pytest.fixture(scope="function")
def test_db():
    """임시 데이터베이스 생성"""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    db_url = f"sqlite:///{db_path}"
    engine = init_db(db_url, echo=False)

    yield engine

    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestCycleDBIntegration:
    """Cycle Analyzer와 Database 통합 테스트"""

    def test_analyzer_to_db_pipeline(self, test_db):
        """완전한 파이프라인 테스트: Analyzer → Repository → DB"""

        # Step 1: Toyo Cycle 분석
        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"
        config = CycleConfig(
            raw_file_path=path,
            mincapacity=0,  # 자동 계산
            firstCrate=0.2,
            chkir=False
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 분석 결과 검증
        assert result.mincapacity > 0, "Capacity should be calculated"
        assert not result.data.empty, "Data should not be empty"
        cycle_count = len(result.data)
        assert cycle_count > 0, "Should have cycles"

        print(f"\n=== Analyzer Results ===")
        print(f"Capacity: {result.mincapacity:.1f} mAh")
        print(f"Cycles: {cycle_count}")

        # Step 2: Database 저장
        with session_scope() as session:
            # Project 생성
            project_repo = TestProjectRepository(session)
            project = project_repo.create(
                name="ATL Q7M Inner 2C Test",
                description="상온수명 테스트 (1-100 cycles)"
            )

            # TestRun 생성
            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path=config.raw_file_path,
                channel_name="30",
                cycler_type="TOYO",
                capacity_mah=result.mincapacity,
                cycle_range_start=1,
                cycle_range_end=cycle_count
            )

            # CycleData 배치 생성
            cycle_repo = CycleDataRepository(session)
            cycle_data_list = []

            for idx, row in result.data.iterrows():
                cycle_data_list.append({
                    "cycle_number": int(row["TotlCycle"]) if "TotlCycle" in row and pd.notna(row["TotlCycle"]) else idx + 1,
                    "original_cycle": int(row["OriCyc"]) if "OriCyc" in row and pd.notna(row["OriCyc"]) else idx + 1,
                    "chg_capacity": float(row["Chg"] * result.mincapacity) if pd.notna(row["Chg"]) else None,
                    "dchg_capacity": float(row["Dchg"] * result.mincapacity) if pd.notna(row["Dchg"]) else None,
                    "dchg_energy": float(row["DchgEng"]) if pd.notna(row["DchgEng"]) else None,
                    "efficiency_chg_dchg": float(row["Eff"] * 100) if pd.notna(row["Eff"]) else None,
                    "efficiency_dchg_chg": float(row["Eff2"] * 100) if pd.notna(row.get("Eff2", float('nan'))) else None,
                    "rest_end_voltage": float(row["RndV"]) if pd.notna(row["RndV"]) else None,
                    "avg_voltage": float(row["AvgV"]) if pd.notna(row["AvgV"]) else None,
                    "temperature": float(row["Temp"]) if pd.notna(row["Temp"]) else None,
                    "dcir": float(row["dcir"]) if "dcir" in row and pd.notna(row["dcir"]) else None
                })

            cycles = cycle_repo.create_batch(test_run.id, cycle_data_list)

            assert len(cycles) == cycle_count, "All cycles should be saved"

            print(f"\n=== DB Storage ===")
            print(f"Project ID: {project.id}")
            print(f"TestRun ID: {test_run.id}")
            print(f"Saved Cycles: {len(cycles)}")

        # Step 3: Database 조회 및 검증
        with session_scope() as session:
            # Project 조회
            project_repo = TestProjectRepository(session)
            retrieved_project = project_repo.get_by_name("ATL Q7M Inner 2C Test")
            assert retrieved_project is not None, "Project should be retrievable"

            # TestRun 조회
            run_repo = TestRunRepository(session)
            runs = run_repo.get_by_project(retrieved_project.id)
            assert len(runs) == 1, "Should have one test run"
            retrieved_run = runs[0]

            # CycleData 조회 (DataFrame)
            cycle_repo = CycleDataRepository(session)
            trend_df = cycle_repo.get_capacity_trend(retrieved_run.id)

            assert len(trend_df) == cycle_count, "Should retrieve all cycles"
            assert "cycle_number" in trend_df.columns
            assert "dchg_capacity" in trend_df.columns
            assert "efficiency" in trend_df.columns

            # 데이터 무결성 검증
            # 원본 분석 결과와 DB 저장 결과 비교
            first_complete_cycle = None
            for idx, row in result.data.iterrows():
                if pd.notna(row["Chg"]) and pd.notna(row["Dchg"]) and row["Chg"] > 0:
                    first_complete_cycle = row
                    cycle_num = int(row["TotlCycle"]) if "TotlCycle" in row and pd.notna(row["TotlCycle"]) else idx + 1
                    break

            if first_complete_cycle is not None:
                db_cycle = trend_df[trend_df["cycle_number"] == cycle_num].iloc[0]

                # 용량 비교 (normalized * mincapacity)
                expected_dchg = first_complete_cycle["Dchg"] * result.mincapacity
                actual_dchg = db_cycle["dchg_capacity"]
                assert abs(expected_dchg - actual_dchg) < 0.1, "Discharge capacity should match"

                # 효율 비교 (ratio * 100)
                expected_eff = first_complete_cycle["Eff"] * 100
                actual_eff = db_cycle["efficiency"]
                assert abs(expected_eff - actual_eff) < 0.1, "Efficiency should match"

            print(f"\n=== DB Query Results ===")
            print(f"Retrieved Project: {retrieved_project.name}")
            print(f"Retrieved Cycles: {len(trend_df)}")
            print(f"Avg Discharge Capacity: {trend_df['dchg_capacity'].mean():.2f} mAh")
            print(f"Avg Efficiency: {trend_df['efficiency'].mean():.2f}%")
            print(f"\nFirst 5 cycles from DB:")
            print(trend_df.head())

    def test_batch_performance(self, test_db):
        """배치 작업 성능 테스트"""

        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"
        config = CycleConfig(raw_file_path=path, mincapacity=0, firstCrate=0.2, chkir=False)

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        import time

        with session_scope() as session:
            # Project & TestRun 생성
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Batch Performance Test")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path=config.raw_file_path,
                cycler_type="TOYO",
                capacity_mah=result.mincapacity
            )

            # 배치 저장 시간 측정
            cycle_repo = CycleDataRepository(session)
            cycle_data_list = []

            for idx, row in result.data.iterrows():
                cycle_data_list.append({
                    "cycle_number": idx + 1,
                    "dchg_capacity": float(row["Dchg"] * result.mincapacity) if pd.notna(row["Dchg"]) else None,
                    "efficiency_chg_dchg": float(row["Eff"] * 100) if pd.notna(row["Eff"]) else None
                })

            start_time = time.time()
            cycles = cycle_repo.create_batch(test_run.id, cycle_data_list)
            batch_time = time.time() - start_time

            assert len(cycles) == len(result.data), "All cycles should be saved"

            print(f"\n=== Batch Performance ===")
            print(f"Cycles: {len(cycles)}")
            print(f"Batch Insert Time: {batch_time:.3f}s")
            print(f"Time per Cycle: {batch_time / len(cycles) * 1000:.2f}ms")

            # 성능 기준: 100 cycles < 1s
            assert batch_time < 1.0, "Batch insert should be fast (<1s for 100 cycles)"

    def test_data_integrity_constraints(self, test_db):
        """데이터 무결성 제약조건 테스트"""

        # 정상 생성 테스트
        with session_scope() as session:
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Integrity Test")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            cycle_repo = CycleDataRepository(session)
            cycle1 = cycle_repo.create(
                test_run_id=test_run.id,
                cycle_number=1,
                dchg_capacity=2000.0
            )
            assert cycle1.id is not None
            session.flush()
            test_run_id = test_run.id

        # 중복 방지 테스트 (test_run_id + cycle_number 유니크)
        # 별도 세션에서 중복 생성 시도
        try:
            with session_scope() as session:
                cycle_repo = CycleDataRepository(session)
                cycle2 = cycle_repo.create(
                    test_run_id=test_run_id,
                    cycle_number=1,  # 중복
                    dchg_capacity=1900.0
                )
                session.flush()
                # 여기 도달하면 안됨
                assert False, "Should have raised IntegrityError"
        except Exception as e:
            # IntegrityError 또는 PendingRollbackError 예상
            assert "UNIQUE constraint" in str(e) or "IntegrityError" in str(e.__class__.__name__)

        print(f"\n=== Integrity Constraints ===")
        print(f"[OK] Unique constraint enforced (test_run_id + cycle_number)")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
