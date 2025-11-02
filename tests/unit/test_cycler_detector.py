"""
Cycler Detector 단위 테스트
"""

import pytest
import sys
import os

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.cycler_detector import detect_cycler_type, get_channel_folders
from src.utils.config_models import CyclerType


class TestCyclerDetector:
    """Cycler Detector 테스트 클래스"""

    def test_detect_toyo_continuous_paths(self):
        """Toyo 연속 경로 타입 감지"""
        paths = [
            "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc",
            "Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc",
            "Rawdata/250304_250404_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 201-300cyc",
            "Rawdata/250317_251231_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 301-400cyc"
        ]

        for path in paths:
            cycler_type = detect_cycler_type(path)
            assert cycler_type == CyclerType.TOYO, f"Expected TOYO but got {cycler_type.value} for {path}"

    def test_detect_pne_continuous_paths(self):
        """PNE 연속 경로 타입 감지"""
        paths = [
            "Rawdata/A1_MP1_4500mAh_T23_1",
            "Rawdata/A1_MP1_4500mAh_T23_2",
            "Rawdata/A1_MP1_4500mAh_T23_3"
        ]

        for path in paths:
            cycler_type = detect_cycler_type(path)
            assert cycler_type == CyclerType.PNE, f"Expected PNE but got {cycler_type.value} for {path}"

    def test_detect_toyo_single_path(self):
        """Toyo 단일 경로 타입 감지"""
        path = "Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r"
        cycler_type = detect_cycler_type(path)
        assert cycler_type == CyclerType.TOYO

    def test_get_toyo_channels(self):
        """Toyo 채널 폴더 추출"""
        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc"

        channels = get_channel_folders(path, CyclerType.TOYO)

        assert len(channels) > 0, "No channels found"
        assert '30' in channels, "Channel 30 not found"
        assert '31' in channels, "Channel 31 not found"
        # 숫자 순으로 정렬되어야 함
        assert channels == sorted(channels, key=int)

    def test_get_pne_channels(self):
        """PNE 채널 폴더 추출"""
        path = "Rawdata/A1_MP1_4500mAh_T23_1"

        channels = get_channel_folders(path, CyclerType.PNE)

        assert len(channels) > 0, "No channels found"
        assert 'M02Ch073[073]' in channels, "Channel M02Ch073[073] not found"
        assert 'M02Ch074[074]' in channels, "Channel M02Ch074[074] not found"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
