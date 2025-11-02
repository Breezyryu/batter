"""
Toyo Rate Profile Loader 단위 테스트
"""

import pytest
import sys
import os

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.toyo_loader import ToyoRateProfileLoader
from src.utils.config_models import ProfileConfig


class TestToyoRateProfileLoader:
    """Toyo Rate Profile Loader 테스트 클래스"""

    def test_load_toyo_rate_profile_single_path(self):
        """Toyo 단일 경로 Rate Profile 로딩 테스트"""

        # Q7M Sub ATL 경로 (Toyo)
        path = "Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r/10"

        # Config 설정
        config = ProfileConfig(
            raw_file_path=path,
            inicycle=10,  # 10번째 사이클
            mincapacity=0,  # 자동 계산
            cutoff=0.05,    # 0.05C cutoff
            inirate=0.2,    # 0.2C로 용량 계산
            smoothdegree=0  # 자동
        )

        # Loader 생성 및 실행
        loader = ToyoRateProfileLoader(config)
        result = loader.load_profile()

        # 검증
        assert result.mincapacity > 0, "Capacity should be calculated"
        assert not result.data.empty, "Data should not be empty"

        # 컬럼 확인
        expected_cols = ["TimeMin", "SOC", "Vol", "Crate", "Temp"]
        assert list(result.data.columns) == expected_cols, f"Expected columns {expected_cols}"

        # 데이터 타입 확인
        assert result.data["TimeMin"].dtype == float, "TimeMin should be float"
        assert result.data["SOC"].dtype == float, "SOC should be float"

        # 범위 확인
        assert result.data["SOC"].min() >= 0, "SOC should be >= 0"
        assert result.data["SOC"].max() <= 1.1, "SOC should be <= 1.1 (allowing some overshoot)"

        # 메타데이터 확인
        assert result.metadata["capacity_mah"] == result.mincapacity
        assert result.metadata["cycle_range"] == (10, None)

        # 결과 출력
        print(f"\nCapacity: {result.mincapacity} mAh")
        print(f"Data points: {len(result.data)}")
        print(f"SOC range: {result.data['SOC'].min():.3f} ~ {result.data['SOC'].max():.3f}")
        print(f"\nFirst 5 rows:")
        print(result.data.head())

    def test_toyo_rate_profile_metadata(self):
        """메타데이터 검증"""

        path = "Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r/10"

        config = ProfileConfig(
            raw_file_path=path,
            inicycle=10,
            mincapacity=2000,  # 수동 지정
            cutoff=0.05,
            inirate=0.2
        )

        loader = ToyoRateProfileLoader(config)
        result = loader.load_profile()

        # 메타데이터 검증
        assert result.metadata["vendor"] == "ToyoRateProfileLoader"
        assert result.metadata["capacity_mah"] == 2000  # 수동 지정 값
        assert result.metadata["cutoff"] == 0.05
        assert result.metadata["inirate"] == 0.2


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
