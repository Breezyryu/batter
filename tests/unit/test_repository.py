"""
Repository Pattern 단위 테스트

CRUD 작업, 쿼리 헬퍼, 배치 작업 검증
"""

import pytest
import sys
import os
import tempfile
import pandas as pd

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.models import TestProject, TestRun, CycleData, ProfileData, ProfileTimeSeries
from src.database.session import init_db, get_session, session_scope
from src.database.repository import (
    TestProjectRepository,
    TestRunRepository,
    CycleDataRepository,
    ProfileDataRepository,
    ProfileTimeSeriesRepository
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


class TestProjectRepository_Test:
    """TestProjectRepository 테스트"""

    def test_create_project(self, test_db):
        """프로젝트 생성 테스트"""
        with session_scope() as session:
            repo = TestProjectRepository(session)
            project = repo.create(
                name="ATL Q7M Inner 2C",
                description="상온수명 테스트"
            )

            assert project.id is not None
            assert project.name == "ATL Q7M Inner 2C"
            assert project.description == "상온수명 테스트"

    def test_get_by_name(self, test_db):
        """이름으로 프로젝트 조회 테스트"""
        with session_scope() as session:
            repo = TestProjectRepository(session)
            project = repo.create(name="Test Project")
            session.commit()

        with session_scope() as session:
            repo = TestProjectRepository(session)
            found = repo.get_by_name("Test Project")
            assert found is not None
            assert found.name == "Test Project"

    def test_get_all(self, test_db):
        """모든 프로젝트 조회 테스트"""
        with session_scope() as session:
            repo = TestProjectRepository(session)
            repo.create(name="Project 1")
            repo.create(name="Project 2")
            repo.create(name="Project 3")
            session.commit()

        with session_scope() as session:
            repo = TestProjectRepository(session)
            projects = repo.get_all()
            assert len(projects) == 3


class TestRunRepository_Test:
    """TestRunRepository 테스트"""

    def test_create_test_run(self, test_db):
        """테스트 실행 생성"""
        with session_scope() as session:
            # Project 생성
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            # TestRun 생성
            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r",
                channel_name="30",
                cycler_type="TOYO",
                capacity_mah=2068.0
            )

            assert test_run.id is not None
            assert test_run.cycler_type == "TOYO"
            assert test_run.capacity_mah == 2068.0

    def test_get_by_project(self, test_db):
        """프로젝트별 테스트 실행 조회"""
        with session_scope() as session:
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/path1",
                cycler_type="TOYO"
            )
            run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/path2",
                cycler_type="TOYO"
            )
            session.commit()

        with session_scope() as session:
            run_repo = TestRunRepository(session)
            runs = run_repo.get_by_project(project.id)
            assert len(runs) == 2


class CycleDataRepository_Test:
    """CycleDataRepository 테스트"""

    def test_create_cycle_data(self, test_db):
        """사이클 데이터 생성"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            # CycleData 생성
            cycle_repo = CycleDataRepository(session)
            cycle_data = cycle_repo.create(
                test_run_id=test_run.id,
                cycle_number=10,
                chg_capacity=2050.0,
                dchg_capacity=2000.0,
                efficiency_chg_dchg=97.5
            )

            assert cycle_data.id is not None
            assert cycle_data.cycle_number == 10
            assert cycle_data.dchg_capacity == 2000.0

    def test_create_batch(self, test_db):
        """배치 생성 테스트"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            # 배치 생성
            cycle_repo = CycleDataRepository(session)
            cycle_data_list = [
                {"cycle_number": i, "dchg_capacity": 2000.0 - i * 10}
                for i in range(1, 11)
            ]
            cycles = cycle_repo.create_batch(test_run.id, cycle_data_list)

            assert len(cycles) == 10
            assert cycles[0].cycle_number == 1
            assert cycles[9].cycle_number == 10

    def test_get_capacity_trend(self, test_db):
        """용량 트렌드 조회 (DataFrame)"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            # 데이터 생성
            cycle_repo = CycleDataRepository(session)
            for i in range(1, 6):
                cycle_repo.create(
                    test_run_id=test_run.id,
                    cycle_number=i,
                    dchg_capacity=2000.0 - i * 10.0,
                    efficiency_chg_dchg=98.0 - i * 0.1
                )
            session.commit()

        with session_scope() as session:
            cycle_repo = CycleDataRepository(session)
            trend_df = cycle_repo.get_capacity_trend(test_run.id)

            assert len(trend_df) == 5
            assert "cycle_number" in trend_df.columns
            assert "dchg_capacity" in trend_df.columns
            assert trend_df.iloc[0]["dchg_capacity"] == 1990.0


class ProfileDataRepository_Test:
    """ProfileDataRepository 테스트"""

    def test_create_profile_data(self, test_db):
        """프로파일 데이터 생성"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            # ProfileData 생성
            profile_repo = ProfileDataRepository(session)
            profile_data = profile_repo.create(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=10,
                cutoff=0.05,
                inirate=0.2,
                data_points=193
            )

            assert profile_data.id is not None
            assert profile_data.profile_type == "rate"
            assert profile_data.data_points == 193

    def test_get_by_test_run_filtered(self, test_db):
        """테스트 실행별 프로파일 조회 (타입 필터)"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            # 여러 타입의 프로파일 생성
            profile_repo = ProfileDataRepository(session)
            profile_repo.create(test_run_id=test_run.id, profile_type="rate", cycle_number=10)
            profile_repo.create(test_run_id=test_run.id, profile_type="step", cycle_number=10)
            profile_repo.create(test_run_id=test_run.id, profile_type="rate", cycle_number=20)
            session.commit()

        with session_scope() as session:
            profile_repo = ProfileDataRepository(session)
            rate_profiles = profile_repo.get_by_test_run(test_run.id, profile_type="rate")
            assert len(rate_profiles) == 2


class ProfileTimeSeriesRepository_Test:
    """ProfileTimeSeriesRepository 테스트"""

    def test_create_from_dataframe(self, test_db):
        """DataFrame으로부터 시계열 데이터 생성"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            profile_repo = ProfileDataRepository(session)
            profile_data = profile_repo.create(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=10
            )

            # DataFrame 생성
            df = pd.DataFrame({
                "TimeMin": [0.0, 1.0, 2.0],
                "SOC": [0.0, 0.1, 0.2],
                "Vol": [3.5, 3.6, 3.7],
                "Crate": [0.2, 0.2, 0.2],
                "Temp": [25.0, 25.5, 26.0]
            })

            # DataFrame에서 시계열 생성
            ts_repo = ProfileTimeSeriesRepository(session)
            timeseries = ts_repo.create_from_dataframe(profile_data.id, df)

            assert len(timeseries) == 3
            assert timeseries[0].time_min == 0.0
            assert timeseries[2].soc == 0.2

    def test_get_as_dataframe(self, test_db):
        """시계열 데이터를 DataFrame으로 조회"""
        with session_scope() as session:
            # Setup
            project_repo = TestProjectRepository(session)
            project = project_repo.create(name="Test Project")

            run_repo = TestRunRepository(session)
            test_run = run_repo.create(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )

            profile_repo = ProfileDataRepository(session)
            profile_data = profile_repo.create(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=10
            )

            # 시계열 데이터 생성
            ts_repo = ProfileTimeSeriesRepository(session)
            df_input = pd.DataFrame({
                "TimeMin": [0.0, 1.0, 2.0],
                "SOC": [0.0, 0.1, 0.2],
                "Vol": [3.5, 3.6, 3.7],
                "Crate": [0.2, 0.2, 0.2],
                "Temp": [25.0, 25.5, 26.0]
            })
            ts_repo.create_from_dataframe(profile_data.id, df_input)
            session.commit()

        # DataFrame으로 조회
        with session_scope() as session:
            ts_repo = ProfileTimeSeriesRepository(session)
            df_output = ts_repo.get_as_dataframe(profile_data.id)

            assert len(df_output) == 3
            assert list(df_output.columns) == ["TimeMin", "SOC", "Vol", "Crate", "Temp"]
            assert df_output.iloc[0]["TimeMin"] == 0.0
            assert df_output.iloc[2]["SOC"] == 0.2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
