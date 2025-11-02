"""
Toyo Cycle Analyzer 단위 테스트

실제 Toyo Rawdata로 사이클 분석 기능 검증
"""

import pytest
import sys
import os
import pandas as pd

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.toyo_cycle_analyzer import ToyoCycleAnalyzer
from src.utils.config_models import CycleConfig


class TestToyoCycleAnalyzer:
    """Toyo Cycle Analyzer 테스트"""

    def test_analyze_toyo_continuous_path_single(self):
        """Toyo 연속 경로 (단일) 사이클 분석 테스트"""

        # Toyo 연속 경로 첫 번째 (1-100cyc)
        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

        # Config 설정
        config = CycleConfig(
            raw_file_path=path,
            mincapacity=0,  # 자동 계산
            firstCrate=0.2,
            chkir=False
        )

        # Analyzer 실행
        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 검증
        assert result.mincapacity > 0, "Capacity should be calculated"
        assert not result.data.empty, "Data should not be empty"

        # 필수 컬럼 확인
        expected_cols = ["Dchg", "RndV", "Eff", "Chg", "DchgEng", "Eff2", "Temp", "AvgV", "OriCyc"]
        for col in expected_cols:
            assert col in result.data.columns, f"Column {col} should exist"

        # 데이터 범위 확인
        assert result.data["Dchg"].min() >= 0, "Discharge capacity should be >= 0"
        assert result.data["Dchg"].max() <= 2.0, "Normalized discharge capacity should be <= 2.0"
        assert result.data["Eff"].min() >= 0, "Efficiency should be >= 0"
        assert result.data["Eff"].max() <= 1.5, "Efficiency should be reasonable"

        # 결과 출력
        print(f"\n=== Toyo Cycle Analysis Results ===")
        print(f"Path: {path}")
        print(f"Capacity: {result.mincapacity:.1f} mAh")
        print(f"Cycles analyzed: {len(result.data)}")
        print(f"Avg discharge capacity: {result.data['Dchg'].mean():.3f} (normalized)")
        print(f"Avg efficiency: {result.data['Eff'].mean() * 100:.2f}%")
        print(f"\nFirst 5 cycles:")
        print(result.data.head())

    def test_capacity_calculation(self):
        """용량 자동 계산 테스트"""

        # 경로명에 용량 정보 포함된 경로
        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

        config = CycleConfig(
            raw_file_path=path,
            mincapacity=0,  # 자동 계산
            firstCrate=0.2
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 경로명의 1689mAh와 유사한 용량이 계산되어야 함
        assert 1600 <= result.mincapacity <= 1800, f"Capacity {result.mincapacity} should be around 1689mAh"

    def test_manual_capacity(self):
        """수동 용량 지정 테스트"""

        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

        config = CycleConfig(
            raw_file_path=path,
            mincapacity=2000.0,  # 수동 지정
            firstCrate=0.2
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 지정한 용량이 사용되어야 함
        assert result.mincapacity == 2000.0, "Manual capacity should be used"

    def test_metadata(self):
        """메타데이터 검증"""

        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

        config = CycleConfig(
            raw_file_path=path,
            mincapacity=1689.0,
            firstCrate=0.2,
            chkir=False
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 메타데이터 검증
        assert result.metadata["vendor"] == "ToyoCycleAnalyzer"
        assert result.metadata["capacity_mah"] == 1689.0
        assert result.metadata["firstCrate"] == 0.2
        assert result.metadata["chkir"] == False
        assert result.metadata["raw_file_path"] == path

    def test_cycle_metrics_calculation(self):
        """사이클 메트릭 계산 검증"""

        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30"

        config = CycleConfig(
            raw_file_path=path,
            mincapacity=0,
            firstCrate=0.2
        )

        analyzer = ToyoCycleAnalyzer(config)
        result = analyzer.analyze()

        # 사이클 메트릭 검증
        assert len(result.data) > 0, "Should have cycle data"

        # 완전한 사이클 찾기 (충전/방전 모두 있는)
        complete_cycle = None
        for idx, row in result.data.iterrows():
            if pd.notna(row["Chg"]) and pd.notna(row["Dchg"]) and row["Chg"] > 0:
                complete_cycle = row
                break

        assert complete_cycle is not None, "Should have at least one complete cycle"

        # 충전/방전 용량 존재 확인
        assert pd.notna(complete_cycle["Chg"]), "Charge capacity should exist"
        assert pd.notna(complete_cycle["Dchg"]), "Discharge capacity should exist"

        # 효율 계산 확인
        calculated_eff = complete_cycle["Dchg"] / complete_cycle["Chg"]
        assert abs(calculated_eff - complete_cycle["Eff"]) < 0.01, "Efficiency should be Dchg/Chg"

        # 방전 에너지 존재 확인
        assert pd.notna(complete_cycle["DchgEng"]), "Discharge energy should exist"

        # 온도 데이터 확인
        assert pd.notna(complete_cycle["Temp"]), "Temperature should exist"

        print(f"\n=== Complete Cycle Metrics ===")
        print(f"Charge: {complete_cycle['Chg']:.3f} (normalized)")
        print(f"Discharge: {complete_cycle['Dchg']:.3f} (normalized)")
        print(f"Efficiency: {complete_cycle['Eff'] * 100:.2f}%")
        print(f"Energy: {complete_cycle['DchgEng']:.1f} mWh")
        print(f"Temperature: {complete_cycle['Temp']:.1f} °C")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
