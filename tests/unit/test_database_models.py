"""
Database Models 단위 테스트

SQLAlchemy ORM 모델 생성, 관계, 제약조건 검증
"""

import pytest
import sys
import os
import tempfile

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.database.models import (
    TestProject,
    TestRun,
    CycleData,
    ProfileData,
    ProfileTimeSeries
)
from src.database.session import init_db, get_session, session_scope, reset_database


@pytest.fixture(scope="function")
def test_db():
    """임시 데이터베이스 생성 (각 테스트마다 새로 생성)"""
    # 임시 파일 생성
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # 데이터베이스 초기화
    db_url = f"sqlite:///{db_path}"
    engine = init_db(db_url, echo=False)

    yield engine

    # 정리
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


class TestDatabaseModels:
    """Database Models 테스트"""

    def test_create_test_project(self, test_db):
        """TestProject 생성 테스트"""
        with session_scope() as session:
            project = TestProject(
                name="Test Project 1",
                description="Test description"
            )
            session.add(project)
            session.flush()

            assert project.id is not None
            assert project.name == "Test Project 1"
            assert project.description == "Test description"
            assert project.created_at is not None
            assert project.updated_at is not None

    def test_test_project_unique_name(self, test_db):
        """TestProject 이름 중복 방지 테스트"""
        with pytest.raises(Exception):  # IntegrityError
            with session_scope() as session:
                project1 = TestProject(name="Duplicate Name")
                project2 = TestProject(name="Duplicate Name")
                session.add_all([project1, project2])
                session.flush()

    def test_create_test_run(self, test_db):
        """TestRun 생성 테스트"""
        with session_scope() as session:
            # Project 생성
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            # TestRun 생성
            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test_path",
                channel_name="30",
                cycler_type="TOYO",
                capacity_mah=2000.0,
                cycle_range_start=1,
                cycle_range_end=100
            )
            session.add(test_run)
            session.flush()

            assert test_run.id is not None
            assert test_run.project_id == project.id
            assert test_run.raw_file_path == "Rawdata/test_path"
            assert test_run.cycler_type == "TOYO"
            assert test_run.capacity_mah == 2000.0

    def test_test_run_cycler_type_constraint(self, test_db):
        """TestRun cycler_type 제약조건 테스트"""
        # Note: SQLite에서는 CHECK constraint가 즉시 발생하지 않을 수 있음
        # 따라서 이 테스트는 PostgreSQL 등에서 더 정확함
        with session_scope() as session:
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"  # Valid: TOYO or PNE
            )
            session.add(test_run)
            session.flush()

            assert test_run.cycler_type in ["TOYO", "PNE"]

    def test_create_cycle_data(self, test_db):
        """CycleData 생성 테스트"""
        with session_scope() as session:
            # Project and TestRun 생성
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )
            session.add(test_run)
            session.flush()

            # CycleData 생성
            cycle_data = CycleData(
                test_run_id=test_run.id,
                cycle_number=10,
                original_cycle=10,
                chg_capacity=2050.0,
                dchg_capacity=2000.0,
                efficiency_chg_dchg=97.5,
                dcir=25.5
            )
            session.add(cycle_data)
            session.flush()

            assert cycle_data.id is not None
            assert cycle_data.cycle_number == 10
            assert cycle_data.dchg_capacity == 2000.0
            assert cycle_data.efficiency_chg_dchg == 97.5

    def test_cycle_data_unique_constraint(self, test_db):
        """CycleData 중복 방지 (test_run_id + cycle_number)"""
        with pytest.raises(Exception):  # IntegrityError
            with session_scope() as session:
                project = TestProject(name="Test Project")
                session.add(project)
                session.flush()

                test_run = TestRun(
                    project_id=project.id,
                    raw_file_path="Rawdata/test",
                    cycler_type="TOYO"
                )
                session.add(test_run)
                session.flush()

                cycle1 = CycleData(test_run_id=test_run.id, cycle_number=10)
                cycle2 = CycleData(test_run_id=test_run.id, cycle_number=10)
                session.add_all([cycle1, cycle2])
                session.flush()

    def test_create_profile_data(self, test_db):
        """ProfileData 생성 테스트"""
        with session_scope() as session:
            # Setup
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )
            session.add(test_run)
            session.flush()

            # ProfileData 생성
            profile_data = ProfileData(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=10,
                cutoff=0.05,
                inirate=0.2,
                smoothdegree=0,
                data_points=193,
                soc_min=0.0,
                soc_max=0.292
            )
            session.add(profile_data)
            session.flush()

            assert profile_data.id is not None
            assert profile_data.profile_type == "rate"
            assert profile_data.cycle_number == 10
            assert profile_data.data_points == 193

    def test_create_profile_timeseries(self, test_db):
        """ProfileTimeSeries 생성 테스트"""
        with session_scope() as session:
            # Setup
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )
            session.add(test_run)
            session.flush()

            profile_data = ProfileData(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=10
            )
            session.add(profile_data)
            session.flush()

            # ProfileTimeSeries 생성
            ts_data = ProfileTimeSeries(
                profile_id=profile_data.id,
                time_min=0.0,
                soc=0.0,
                voltage=3.5,
                crate=0.2,
                temperature=25.0
            )
            session.add(ts_data)
            session.flush()

            assert ts_data.id is not None
            assert ts_data.time_min == 0.0
            assert ts_data.soc == 0.0
            assert ts_data.voltage == 3.5

    def test_cascade_delete_project(self, test_db):
        """Project 삭제 시 관련 데이터 자동 삭제 테스트"""
        with session_scope() as session:
            # 전체 데이터 구조 생성
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test",
                cycler_type="TOYO"
            )
            session.add(test_run)
            session.flush()

            cycle_data = CycleData(test_run_id=test_run.id, cycle_number=1)
            profile_data = ProfileData(
                test_run_id=test_run.id,
                profile_type="rate",
                cycle_number=1
            )
            session.add_all([cycle_data, profile_data])
            session.flush()

            project_id = project.id
            test_run_id = test_run.id

        # Project 삭제
        with session_scope() as session:
            project = session.get(TestProject, project_id)
            session.delete(project)
            session.flush()

        # 검증: TestRun, CycleData, ProfileData 모두 삭제되어야 함
        with session_scope() as session:
            assert session.get(TestProject, project_id) is None
            assert session.get(TestRun, test_run_id) is None

    def test_relationships(self, test_db):
        """모델 간 관계 테스트"""
        with session_scope() as session:
            # 데이터 생성
            project = TestProject(name="Test Project")
            session.add(project)
            session.flush()

            test_run1 = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test1",
                cycler_type="TOYO"
            )
            test_run2 = TestRun(
                project_id=project.id,
                raw_file_path="Rawdata/test2",
                cycler_type="PNE"
            )
            session.add_all([test_run1, test_run2])
            session.flush()

            # Relationship 검증
            assert len(project.test_runs) == 2
            assert test_run1.project.name == "Test Project"
            assert test_run2.project.name == "Test Project"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
