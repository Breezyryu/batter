"""
Configuration models using dataclasses
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
import pandas as pd


class CyclerType(Enum):
    """배터리 충방전기 타입"""
    TOYO = "toyo"
    PNE = "pne"


@dataclass
class ProfileConfig:
    """
    프로파일 데이터 로딩 설정

    Attributes:
        raw_file_path: 데이터 폴더 경로
        inicycle: 시작 사이클 번호
        endcycle: 종료 사이클 번호 (None이면 단일 사이클)
        mincapacity: 배터리 용량 (0이면 자동 계산)
        cutoff: 전류 cutoff 값 (C-rate)
        inirate: 초기 C-rate (용량 계산용, 기본 0.2C)
        smoothdegree: dQ/dV 계산용 스무딩 윈도우 (0이면 자동)
    """
    raw_file_path: str
    inicycle: int
    endcycle: Optional[int] = None
    mincapacity: float = 0.0
    cutoff: float = 0.0
    inirate: float = 0.2
    smoothdegree: int = 0


@dataclass
class ProfileResult:
    """
    프로파일 데이터 로딩 결과

    Attributes:
        mincapacity: 계산된 배터리 용량 (mAh)
        data: 프로파일 데이터 DataFrame
        metadata: 추가 메타데이터
    """
    mincapacity: float
    data: pd.DataFrame
    metadata: Optional[Dict] = field(default_factory=dict)


@dataclass
class CycleConfig:
    """
    사이클 데이터 로딩 설정

    Attributes:
        raw_file_path: 데이터 폴더 경로
        mincapacity: 배터리 용량 (0이면 자동 계산)
        firstCrate: 첫 사이클 C-rate (용량 계산용)
        chkir: DCIR 체크 모드
    """
    raw_file_path: str
    mincapacity: float = 0.0
    firstCrate: float = 0.2
    chkir: bool = False


@dataclass
class CycleResult:
    """
    사이클 데이터 로딩 결과

    Attributes:
        mincapacity: 계산된 배터리 용량 (mAh)
        data: 사이클 데이터 DataFrame
        metadata: 추가 메타데이터
    """
    mincapacity: float
    data: pd.DataFrame
    metadata: Optional[Dict] = field(default_factory=dict)


@dataclass
class PathGroup:
    """
    연속 경로 그룹

    Attributes:
        paths: 경로 리스트
        cycler_type: 장비 타입
        channel_names: 채널명 리스트
        is_validated: 채널명 일치성 검증 여부
    """
    paths: List[str]
    cycler_type: CyclerType
    channel_names: List[str] = field(default_factory=list)
    is_validated: bool = False


# 프로파일 타입 Enum
class ProfileType(Enum):
    """프로파일 분석 타입"""
    STEP = "step"
    RATE = "rate"
    CHARGE = "charge"
    DISCHARGE = "discharge"
    CONTINUE = "continue"
    DCIR = "dcir"
