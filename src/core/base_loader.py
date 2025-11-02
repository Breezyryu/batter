"""
Base Profile Loader - Abstract Base Class
7단계 파이프라인 템플릿 정의
"""

from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
from ..utils.config_models import ProfileConfig, ProfileResult


class BaseProfileLoader(ABC):
    """
    배터리 프로파일 데이터 로딩을 위한 추상 기본 클래스

    Template Method Pattern을 사용하여 7단계 공통 파이프라인 정의:
    1. Capacity Calculation → _calculate_capacity()
    2. Data Import → _load_raw_data()
    3. Condition Filtering → _filter_condition()
    4. Cutoff Application → _apply_cutoff()
    5. Capacity Processing → _process_capacity()
    6. Unit Normalization → _normalize_units()
    7. Final Formatting → _format_output()
    """

    def __init__(self, config: ProfileConfig):
        """
        Args:
            config: ProfileConfig 설정 객체
        """
        self.config = config
        self.mincapacity: Optional[float] = None

    # ===== Template Method =====
    def load_profile(self) -> ProfileResult:
        """
        메인 템플릿 메서드 - 7단계 파이프라인 실행

        Returns:
            ProfileResult: 로딩된 프로파일 데이터 결과

        Raises:
            ValueError: 데이터 로딩 실패 시
        """
        # Step 1: Calculate battery capacity
        self.mincapacity = self._calculate_capacity()

        # Step 2: Load raw data from files
        raw_data = self._load_raw_data()
        if raw_data is None or raw_data.empty:
            return ProfileResult(
                mincapacity=self.mincapacity,
                data=pd.DataFrame(),
                metadata={'error': 'No data loaded'}
            )

        # Step 3: Filter by condition (charge/discharge)
        filtered_data = self._filter_condition(raw_data)
        if filtered_data.empty:
            return ProfileResult(
                mincapacity=self.mincapacity,
                data=pd.DataFrame(),
                metadata={'error': 'No data after condition filtering'}
            )

        # Step 4: Apply cutoff filters
        filtered_data = self._apply_cutoff(filtered_data)

        # Step 5: Calculate capacity/SOC
        processed_data = self._process_capacity(filtered_data)

        # Step 6: Normalize units
        normalized_data = self._normalize_units(processed_data)

        # Step 7: Format final output
        final_data = self._format_output(normalized_data)

        return ProfileResult(
            mincapacity=self.mincapacity,
            data=final_data,
            metadata=self._get_metadata()
        )

    # ===== Abstract Methods (장비별 구현 필요) =====
    @abstractmethod
    def _calculate_capacity(self) -> float:
        """
        배터리 용량 계산 (장비별 구현)

        Returns:
            float: 계산된 용량 (mAh)
        """
        pass

    @abstractmethod
    def _load_raw_data(self) -> pd.DataFrame:
        """
        장비별 파일 포맷에서 Raw 데이터 로딩

        Returns:
            pd.DataFrame: 로딩된 원시 데이터
        """
        pass

    @abstractmethod
    def _filter_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        충전/방전 조건 필터링 (장비별 구현)

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 필터링된 DataFrame
        """
        pass

    # ===== Concrete Methods (공통 구현) =====
    def _apply_cutoff(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        전류 또는 전압 cutoff 필터 적용

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: Cutoff 적용된 DataFrame
        """
        if self.config.cutoff == 0:
            return df

        # 서브클래스에서 오버라이드 가능
        return df

    def _integrate_capacity(self, df: pd.DataFrame,
                           time_col: str, current_col: str,
                           cap_col: str) -> pd.DataFrame:
        """
        벡터화된 용량 적분 계산 (공통 알고리즘)

        Args:
            df: 입력 DataFrame
            time_col: 시간 컬럼명 (초 단위)
            current_col: 전류 컬럼명 (mA)
            cap_col: 출력 용량 컬럼명

        Returns:
            pd.DataFrame: 용량이 계산된 DataFrame
        """
        df = df.reset_index(drop=True)
        df[cap_col] = 0.0

        if len(df) < 2:
            return df

        # 벡터화 적분
        initial_cap = df[cap_col].iloc[0]
        df["delta_time"] = df[time_col].shift(-1) - df[time_col]
        df["next_current"] = df[current_col].shift(-1)
        df["contribution"] = (df["delta_time"] * df["next_current"]) / 3600

        df[cap_col] = initial_cap + df["contribution"].fillna(0).cumsum().shift(1, fill_value=0)

        # 임시 컬럼 제거
        df.drop(["delta_time", "next_current", "contribution"], axis=1, inplace=True)

        return df

    def _calculate_dqdv(self, df: pd.DataFrame,
                       vol_col: str = "Voltage[V]",
                       cap_col: str = "Cap[mAh]") -> pd.DataFrame:
        """
        dQ/dV 미분 분석 (공통 알고리즘)

        Args:
            df: 입력 DataFrame
            vol_col: 전압 컬럼명
            cap_col: 용량 컬럼명

        Returns:
            pd.DataFrame: dQ/dV 계산이 추가된 DataFrame
        """
        # 스무딩 윈도우 자동 계산
        smoothdegree = self.config.smoothdegree
        if smoothdegree == 0:
            smoothdegree = max(1, int(len(df) / 30))

        # 미분 분석
        df["delvol"] = df[vol_col].diff(periods=smoothdegree)
        df["delcap"] = df[cap_col].diff(periods=smoothdegree)
        df["dQdV"] = df["delcap"] / df["delvol"]
        df["dVdQ"] = df["delvol"] / df["delcap"]

        return df

    @abstractmethod
    def _process_capacity(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        용량 처리 (프로파일 타입별 구현)

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 처리된 DataFrame
        """
        pass

    @abstractmethod
    def _normalize_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        단위 정규화 (장비별 구현)

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 정규화된 DataFrame
        """
        pass

    @abstractmethod
    def _format_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        최종 출력 포맷팅 (프로파일 타입별 구현)

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 포맷팅된 DataFrame
        """
        pass

    def _get_metadata(self) -> dict:
        """
        메타데이터 생성

        Returns:
            dict: 메타데이터 딕셔너리
        """
        return {
            "vendor": self.__class__.__name__,
            "cycle_range": (self.config.inicycle, self.config.endcycle),
            "capacity_mah": self.mincapacity,
            "cutoff": self.config.cutoff,
            "inirate": self.config.inirate
        }
