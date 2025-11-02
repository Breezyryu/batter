"""
Repository Pattern for Database Operations

Provides clean interface for CRUD operations on battery data.
"""

from typing import List, Optional
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from .models import (
    TestProject,
    TestRun,
    CycleData,
    ProfileData,
    ProfileTimeSeries
)


class TestProjectRepository:
    """Repository for TestProject operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, description: Optional[str] = None) -> TestProject:
        """Create new test project"""
        project = TestProject(name=name, description=description)
        self.session.add(project)
        self.session.flush()
        return project

    def get_by_id(self, project_id: int) -> Optional[TestProject]:
        """Get project by ID"""
        return self.session.get(TestProject, project_id)

    def get_by_name(self, name: str) -> Optional[TestProject]:
        """Get project by name"""
        stmt = select(TestProject).where(TestProject.name == name)
        return self.session.scalars(stmt).first()

    def get_all(self) -> List[TestProject]:
        """Get all projects"""
        stmt = select(TestProject).order_by(TestProject.created_at.desc())
        return list(self.session.scalars(stmt))

    def update(self, project: TestProject, **kwargs) -> TestProject:
        """Update project attributes"""
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        self.session.flush()
        return project

    def delete(self, project: TestProject) -> None:
        """Delete project (cascades to test_runs, cycle_data, profile_data)"""
        self.session.delete(project)
        self.session.flush()


class TestRunRepository:
    """Repository for TestRun operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        project_id: int,
        raw_file_path: str,
        cycler_type: str,
        channel_name: Optional[str] = None,
        capacity_mah: Optional[float] = None,
        cycle_range_start: Optional[int] = None,
        cycle_range_end: Optional[int] = None
    ) -> TestRun:
        """Create new test run"""
        test_run = TestRun(
            project_id=project_id,
            raw_file_path=raw_file_path,
            channel_name=channel_name,
            cycler_type=cycler_type,
            capacity_mah=capacity_mah,
            cycle_range_start=cycle_range_start,
            cycle_range_end=cycle_range_end
        )
        self.session.add(test_run)
        self.session.flush()
        return test_run

    def get_by_id(self, test_run_id: int) -> Optional[TestRun]:
        """Get test run by ID"""
        return self.session.get(TestRun, test_run_id)

    def get_by_path(self, raw_file_path: str, channel_name: Optional[str] = None) -> Optional[TestRun]:
        """Get test run by path and channel"""
        stmt = select(TestRun).where(
            and_(
                TestRun.raw_file_path == raw_file_path,
                TestRun.channel_name == channel_name
            )
        )
        return self.session.scalars(stmt).first()

    def get_by_project(self, project_id: int) -> List[TestRun]:
        """Get all test runs for a project"""
        stmt = select(TestRun).where(TestRun.project_id == project_id)
        return list(self.session.scalars(stmt))

    def get_by_cycler_type(self, cycler_type: str) -> List[TestRun]:
        """Get all test runs for a cycler type"""
        stmt = select(TestRun).where(TestRun.cycler_type == cycler_type)
        return list(self.session.scalars(stmt))

    def delete(self, test_run: TestRun) -> None:
        """Delete test run (cascades to cycle_data, profile_data)"""
        self.session.delete(test_run)
        self.session.flush()


class CycleDataRepository:
    """Repository for CycleData operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, test_run_id: int, cycle_number: int, **kwargs) -> CycleData:
        """Create new cycle data entry"""
        cycle_data = CycleData(
            test_run_id=test_run_id,
            cycle_number=cycle_number,
            **kwargs
        )
        self.session.add(cycle_data)
        self.session.flush()
        return cycle_data

    def create_batch(self, test_run_id: int, cycle_data_list: List[dict]) -> List[CycleData]:
        """Create multiple cycle data entries"""
        entries = [
            CycleData(test_run_id=test_run_id, **data)
            for data in cycle_data_list
        ]
        self.session.add_all(entries)
        self.session.flush()
        return entries

    def get_by_test_run(self, test_run_id: int) -> List[CycleData]:
        """Get all cycle data for a test run"""
        stmt = select(CycleData).where(
            CycleData.test_run_id == test_run_id
        ).order_by(CycleData.cycle_number)
        return list(self.session.scalars(stmt))

    def get_by_cycle(self, test_run_id: int, cycle_number: int) -> Optional[CycleData]:
        """Get cycle data for specific cycle"""
        stmt = select(CycleData).where(
            and_(
                CycleData.test_run_id == test_run_id,
                CycleData.cycle_number == cycle_number
            )
        )
        return self.session.scalars(stmt).first()

    def get_capacity_trend(self, test_run_id: int) -> pd.DataFrame:
        """Get capacity trend as DataFrame"""
        cycles = self.get_by_test_run(test_run_id)
        data = [
            {
                "cycle_number": c.cycle_number,
                "chg_capacity": c.chg_capacity,
                "dchg_capacity": c.dchg_capacity,
                "efficiency": c.efficiency_chg_dchg
            }
            for c in cycles
        ]
        return pd.DataFrame(data)

    def delete_by_test_run(self, test_run_id: int) -> None:
        """Delete all cycle data for a test run"""
        stmt = select(CycleData).where(CycleData.test_run_id == test_run_id)
        for cycle_data in self.session.scalars(stmt):
            self.session.delete(cycle_data)
        self.session.flush()


class ProfileDataRepository:
    """Repository for ProfileData operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        test_run_id: int,
        profile_type: str,
        cycle_number: int,
        **kwargs
    ) -> ProfileData:
        """Create new profile data entry"""
        profile_data = ProfileData(
            test_run_id=test_run_id,
            profile_type=profile_type,
            cycle_number=cycle_number,
            **kwargs
        )
        self.session.add(profile_data)
        self.session.flush()
        return profile_data

    def get_by_id(self, profile_id: int) -> Optional[ProfileData]:
        """Get profile data by ID"""
        return self.session.get(ProfileData, profile_id)

    def get_by_test_run(
        self,
        test_run_id: int,
        profile_type: Optional[str] = None
    ) -> List[ProfileData]:
        """Get all profile data for a test run, optionally filtered by type"""
        stmt = select(ProfileData).where(ProfileData.test_run_id == test_run_id)
        if profile_type:
            stmt = stmt.where(ProfileData.profile_type == profile_type)
        stmt = stmt.order_by(ProfileData.cycle_number)
        return list(self.session.scalars(stmt))

    def get_by_cycle(
        self,
        test_run_id: int,
        profile_type: str,
        cycle_number: int
    ) -> Optional[ProfileData]:
        """Get profile data for specific cycle and type"""
        stmt = select(ProfileData).where(
            and_(
                ProfileData.test_run_id == test_run_id,
                ProfileData.profile_type == profile_type,
                ProfileData.cycle_number == cycle_number
            )
        )
        return self.session.scalars(stmt).first()

    def delete(self, profile_data: ProfileData) -> None:
        """Delete profile data (cascades to timeseries)"""
        self.session.delete(profile_data)
        self.session.flush()


class ProfileTimeSeriesRepository:
    """Repository for ProfileTimeSeries operations"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, profile_id: int, **kwargs) -> ProfileTimeSeries:
        """Create new timeseries data point"""
        ts_data = ProfileTimeSeries(profile_id=profile_id, **kwargs)
        self.session.add(ts_data)
        self.session.flush()
        return ts_data

    def create_batch(self, profile_id: int, data_list: List[dict]) -> List[ProfileTimeSeries]:
        """Create multiple timeseries data points"""
        entries = [
            ProfileTimeSeries(profile_id=profile_id, **data)
            for data in data_list
        ]
        self.session.add_all(entries)
        self.session.flush()
        return entries

    def create_from_dataframe(self, profile_id: int, df: pd.DataFrame) -> List[ProfileTimeSeries]:
        """
        Create timeseries from DataFrame

        Args:
            profile_id: Profile ID
            df: DataFrame with columns [TimeMin, SOC, Vol, Crate, Temp]

        Returns:
            List of created ProfileTimeSeries
        """
        # Column mapping: DataFrame -> DB
        column_map = {
            "TimeMin": "time_min",
            "SOC": "soc",
            "Vol": "voltage",
            "Crate": "crate",
            "Temp": "temperature"
        }

        data_list = []
        for _, row in df.iterrows():
            data = {}
            for df_col, db_col in column_map.items():
                if df_col in df.columns:
                    value = row[df_col]
                    # Handle NaN values
                    if pd.notna(value):
                        data[db_col] = float(value)
            data_list.append(data)

        return self.create_batch(profile_id, data_list)

    def get_by_profile(self, profile_id: int) -> List[ProfileTimeSeries]:
        """Get all timeseries data for a profile"""
        stmt = select(ProfileTimeSeries).where(
            ProfileTimeSeries.profile_id == profile_id
        ).order_by(ProfileTimeSeries.time_min)
        return list(self.session.scalars(stmt))

    def get_as_dataframe(self, profile_id: int) -> pd.DataFrame:
        """
        Get timeseries data as DataFrame

        Returns:
            DataFrame with columns [TimeMin, SOC, Vol, Crate, Temp]
        """
        timeseries = self.get_by_profile(profile_id)
        data = [
            {
                "TimeMin": ts.time_min,
                "SOC": ts.soc,
                "Vol": ts.voltage,
                "Crate": ts.crate,
                "Temp": ts.temperature
            }
            for ts in timeseries
        ]
        return pd.DataFrame(data)

    def delete_by_profile(self, profile_id: int) -> None:
        """Delete all timeseries data for a profile"""
        stmt = select(ProfileTimeSeries).where(ProfileTimeSeries.profile_id == profile_id)
        for ts_data in self.session.scalars(stmt):
            self.session.delete(ts_data)
        self.session.flush()
