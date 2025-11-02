"""
Path Handler 단위 테스트
"""

import pytest
import sys
import os

# src 모듈 import 경로 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.utils.path_handler import PathHandler
from src.utils.config_models import CyclerType


class TestPathHandler:
    """Path Handler 테스트 클래스"""

    def test_validate_toyo_continuous_paths(self):
        """Toyo 연속 경로 채널명 일치성 검증"""
        paths = [
            "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc",
            "Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc",
            "Rawdata/250304_250404_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 201-300cyc",
            "Rawdata/250317_251231_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 301-400cyc"
        ]

        success, message = PathHandler.validate_continuous_paths(paths)

        assert success, f"Validation failed: {message}"
        assert "30" in message or "31" in message, "Channel names not in message"

    def test_validate_pne_continuous_paths(self):
        """PNE 연속 경로 채널명 일치성 검증"""
        paths = [
            "Rawdata/A1_MP1_4500mAh_T23_1",
            "Rawdata/A1_MP1_4500mAh_T23_2",
            "Rawdata/A1_MP1_4500mAh_T23_3"
        ]

        success, message = PathHandler.validate_continuous_paths(paths)

        assert success, f"Validation failed: {message}"
        assert "M02Ch073" in message or "M02Ch074" in message, "Channel names not in message"

    def test_extract_toyo_channel_names(self):
        """Toyo 채널명 추출"""
        path = "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc"

        channels = PathHandler.extract_channel_names(path)

        assert '30' in channels, "Channel 30 not found"
        assert '31' in channels, "Channel 31 not found"

    def test_extract_pne_channel_names(self):
        """PNE 채널명 추출"""
        path = "Rawdata/A1_MP1_4500mAh_T23_1"

        channels = PathHandler.extract_channel_names(path)

        assert 'M02Ch073[073]' in channels, "Channel M02Ch073[073] not found"
        assert 'M02Ch074[074]' in channels, "Channel M02Ch074[074] not found"

    def test_create_toyo_path_group(self):
        """Toyo 경로 그룹 생성"""
        paths = [
            "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc",
            "Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc"
        ]

        path_group = PathHandler.create_path_group(paths, validate=True)

        assert path_group.cycler_type == CyclerType.TOYO
        assert path_group.is_validated == True
        assert len(path_group.channel_names) >= 2  # At least channels 30, 31

    def test_create_pne_path_group(self):
        """PNE 경로 그룹 생성"""
        paths = [
            "Rawdata/A1_MP1_4500mAh_T23_1",
            "Rawdata/A1_MP1_4500mAh_T23_2"
        ]

        path_group = PathHandler.create_path_group(paths, validate=True)

        assert path_group.cycler_type == CyclerType.PNE
        assert path_group.is_validated == True
        assert len(path_group.channel_names) >= 2  # At least 2 channels

    def test_single_path_group(self):
        """단일 경로 그룹 생성"""
        paths = ["Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r"]

        path_group = PathHandler.create_path_group(paths, validate=False)

        assert path_group.cycler_type == CyclerType.TOYO
        assert path_group.is_validated == True  # Single path는 항상 검증됨
        assert len(path_group.channel_names) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
