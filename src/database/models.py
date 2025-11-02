"""
SQLAlchemy ORM Models for Battery Data Analysis System

Tables:
- test_projects: 배터리 테스트 프로젝트
- test_runs: 개별 테스트 실행 (경로, 장비, 용량)
- cycle_data: 사이클별 성능 데이터
- profile_data: 프로파일 분석 결과
- profile_timeseries: 프로파일 시계열 데이터
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    CheckConstraint, UniqueConstraint, Index, Text
)
from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column

Base = declarative_base()


class TestProject(Base):
    """
    배터리 테스트 프로젝트

    프로젝트 단위로 여러 테스트 실행을 그룹화
    예: "ATL Q7M Inner 2C 상온수명"
    """
    __tablename__ = "test_projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    test_runs: Mapped[List["TestRun"]] = relationship(
        "TestRun", back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<TestProject(id={self.id}, name='{self.name}')>"


class TestRun(Base):
    """
    개별 테스트 실행

    Rawdata 경로, 채널, 장비 타입, 용량 정보 저장
    """
    __tablename__ = "test_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_projects.id", ondelete="CASCADE"), nullable=False
    )
    raw_file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cycler_type: Mapped[str] = mapped_column(
        String(10),
        CheckConstraint("cycler_type IN ('TOYO', 'PNE')"),
        nullable=False
    )
    capacity_mah: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cycle_range_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cycle_range_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["TestProject"] = relationship("TestProject", back_populates="test_runs")
    cycle_data: Mapped[List["CycleData"]] = relationship(
        "CycleData", back_populates="test_run", cascade="all, delete-orphan"
    )
    profile_data: Mapped[List["ProfileData"]] = relationship(
        "ProfileData", back_populates="test_run", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("raw_file_path", "channel_name", name="uq_test_run_path_channel"),
        Index("idx_test_runs_project", "project_id"),
        Index("idx_test_runs_cycler", "cycler_type"),
    )

    def __repr__(self) -> str:
        return f"<TestRun(id={self.id}, path='{self.raw_file_path}', cycler='{self.cycler_type}')>"


class CycleData(Base):
    """
    사이클별 성능 데이터

    용량, 효율, DCIR 등 사이클 분석 결과
    Source: BatteryDataTool.py indiv_cyc_confirm_button (line 8208)
    """
    __tablename__ = "cycle_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_cycle: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 용량 데이터
    chg_capacity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mAh
    dchg_capacity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mAh
    dchg_energy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Wh

    # 효율 데이터
    efficiency_chg_dchg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # %
    efficiency_dchg_chg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # %

    # 전압 데이터
    rest_end_voltage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # V
    ocv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # V
    avg_voltage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # V

    # DCIR 데이터
    dcir: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mΩ
    dcir2: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mΩ (PNE)
    rss_ocv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # V
    rss_ccv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # V
    soc70_dcir: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mΩ
    soc70_rss_dcir: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # mΩ

    # 메타데이터
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # ℃
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="cycle_data")

    # Constraints
    __table_args__ = (
        UniqueConstraint("test_run_id", "cycle_number", name="uq_cycle_data_run_cycle"),
        Index("idx_cycle_data_test_run", "test_run_id"),
        Index("idx_cycle_data_cycle_num", "cycle_number"),
        Index("idx_cycle_data_capacity", "dchg_capacity"),
    )

    def __repr__(self) -> str:
        return (
            f"<CycleData(id={self.id}, test_run_id={self.test_run_id}, "
            f"cycle={self.cycle_number}, dchg_cap={self.dchg_capacity})>"
        )


class ProfileData(Base):
    """
    프로파일 분석 결과

    Rate/Step/Charge/Discharge 프로파일 메타데이터
    Source: BatteryDataTool.py rate_confirm_button, step_confirm_button 등
    """
    __tablename__ = "profile_data"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_run_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    profile_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("profile_type IN ('rate', 'step', 'charge', 'discharge', 'continue', 'dcir')"),
        nullable=False
    )
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Profile Config
    cutoff: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inirate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    smoothdegree: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 분석 결과 메타데이터
    data_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    soc_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soc_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # 파일 경로 (옵션: Parquet 저장 시)
    data_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    test_run: Mapped["TestRun"] = relationship("TestRun", back_populates="profile_data")
    timeseries: Mapped[List["ProfileTimeSeries"]] = relationship(
        "ProfileTimeSeries", back_populates="profile", cascade="all, delete-orphan"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("test_run_id", "profile_type", "cycle_number", name="uq_profile_data_run_type_cycle"),
        Index("idx_profile_data_test_run", "test_run_id"),
        Index("idx_profile_data_type", "profile_type"),
        Index("idx_profile_data_cycle", "cycle_number"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProfileData(id={self.id}, test_run_id={self.test_run_id}, "
            f"type='{self.profile_type}', cycle={self.cycle_number})>"
        )


class ProfileTimeSeries(Base):
    """
    프로파일 시계열 데이터

    TimeMin, SOC, Vol, Crate, Temp 데이터 포인트
    Source: Phase 2 ProfileResult.data (toyo_loader.py)
    """
    __tablename__ = "profile_timeseries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("profile_data.id", ondelete="CASCADE"), nullable=False
    )

    # 시계열 데이터
    time_min: Mapped[float] = mapped_column(Float, nullable=False)  # 시간 (분)
    soc: Mapped[float] = mapped_column(Float, nullable=False)  # State of Charge (0~1)
    voltage: Mapped[float] = mapped_column(Float, nullable=False)  # 전압 (V)
    crate: Mapped[float] = mapped_column(Float, nullable=False)  # C-rate
    temperature: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 온도 (℃)

    # 추가 분석 데이터 (옵션)
    dqdv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # dQ/dV (mAh/V)

    # Relationships
    profile: Mapped["ProfileData"] = relationship("ProfileData", back_populates="timeseries")

    # Constraints
    __table_args__ = (
        UniqueConstraint("profile_id", "time_min", name="uq_profile_ts_profile_time"),
        Index("idx_profile_ts_profile", "profile_id"),
        Index("idx_profile_ts_soc", "soc"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProfileTimeSeries(id={self.id}, profile_id={self.profile_id}, "
            f"time={self.time_min:.2f}, soc={self.soc:.3f})>"
        )
