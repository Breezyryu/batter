"""
Toyo 충방전기용 Profile Loader 구현
"""

import os
import pandas as pd
from .base_loader import BaseProfileLoader
from ..legacy.toyo_functions import toyo_min_cap, toyo_Profile_import
from ..utils.config_models import ProfileConfig


class ToyoRateProfileLoader(BaseProfileLoader):
    """
    Toyo Rate Profile Loader

    Rate 테스트 프로파일 분석:
    - 단일 사이클 분석
    - 충전 조건만 (Condition == 1)
    - C-rate 정규화

    Source: BatteryDataTool.py line 809 (toyo_rate_Profile_data)
    """

    def __init__(self, config: ProfileConfig):
        super().__init__(config)

    def _calculate_capacity(self) -> float:
        """
        배터리 용량 계산

        Returns:
            float: 계산된 용량 (mAh)
        """
        return toyo_min_cap(
            self.config.raw_file_path,
            self.config.mincapacity,
            self.config.inirate
        )

    def _load_raw_data(self) -> pd.DataFrame:
        """
        Toyo Profile 데이터 로딩

        Returns:
            pd.DataFrame: 로딩된 데이터
        """
        # 파일 존재 확인
        file_path = self.config.raw_file_path + "\\%06d" % self.config.inicycle
        if not os.path.isfile(file_path):
            return pd.DataFrame()

        # Profile 데이터 불러오기
        tempdata = toyo_Profile_import(
            self.config.raw_file_path,
            self.config.inicycle
        )

        if hasattr(tempdata, 'dataraw') and not tempdata.dataraw.empty:
            return tempdata.dataraw

        return pd.DataFrame()

    def _filter_condition(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        충전 조건 필터링 (Condition == 1)

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 충전 데이터만 필터링
        """
        if "Condition" in df.columns:
            return df[df["Condition"] == 1].copy()
        return df

    def _apply_cutoff(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        전류 cutoff 적용

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: Cutoff 적용된 DataFrame
        """
        if self.config.cutoff > 0 and "Current[mA]" in df.columns:
            cutoff_current = self.config.cutoff * self.mincapacity
            return df[df["Current[mA]"] >= cutoff_current].copy()
        return df

    def _process_capacity(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        용량 계산

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 용량이 계산된 DataFrame
        """
        # 초기화
        df = df.reset_index(drop=True)
        df["Cap[mAh]"] = 0.0

        if len(df) < 2:
            return df

        # Base class의 integrate_capacity 사용
        df = self._integrate_capacity(df, "PassTime[Sec]", "Current[mA]", "Cap[mAh]")

        # 추가 용량 계산 (원본 코드와 동일)
        if len(df) > 1:
            # PassTime[Sec]의 차이 계산
            time_diffs = df["PassTime[Sec]"].diff().iloc[1:]
            # (시간 차이 / 3600) * Current[mA] 계산
            increments = (time_diffs / 3600) * df["Current[mA]"].iloc[1:]
            # 누적 합 계산
            cum_increments = increments.cumsum()
            # 첫 행의 Cap[mAh] 값
            initial_cap = df["Cap[mAh]"].iloc[0]
            # 두 번째 행부터 업데이트
            df.iloc[1:, df.columns.get_loc("Cap[mAh]")] = initial_cap + cum_increments.values

        return df

    def _normalize_units(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        단위 정규화

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 정규화된 DataFrame
        """
        # 시간: 초 → 분
        if "PassTime[Sec]" in df.columns:
            df["PassTime[Sec]"] = df["PassTime[Sec]"] / 60

        # 전류: mA → C-rate
        if "Current[mA]" in df.columns:
            df["Current[mA]"] = df["Current[mA]"] / self.mincapacity

        # 용량: mAh → SOC (0~1)
        if "Cap[mAh]" in df.columns:
            df["Cap[mAh]"] = df["Cap[mAh]"] / self.mincapacity

        return df

    def _format_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        최종 출력 포맷팅

        Args:
            df: 입력 DataFrame

        Returns:
            pd.DataFrame: 포맷팅된 DataFrame
        """
        # 필요한 컬럼만 선택
        output_cols = ["PassTime[Sec]", "Cap[mAh]", "Voltage[V]", "Current[mA]", "Temp1[Deg]"]
        df = df[output_cols].copy()

        # 컬럼명 변경
        df.columns = ["TimeMin", "SOC", "Vol", "Crate", "Temp"]

        return df
