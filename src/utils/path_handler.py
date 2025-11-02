"""
경로 처리 및 채널명 매칭 검증 모듈
"""

import os
from typing import List, Tuple
from .config_models import CyclerType, PathGroup
from ..core.cycler_detector import detect_cycler_type, get_channel_folders


class PathHandler:
    """경로 처리 및 검증 클래스"""

    @staticmethod
    def validate_continuous_paths(paths: List[str]) -> Tuple[bool, str]:
        """
        연속 경로의 채널명 일치성 검증

        Args:
            paths: 경로 리스트

        Returns:
            Tuple[bool, str]: (검증 성공 여부, 메시지)

        Example:
            >>> paths = [
            ...     "Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc",
            ...     "Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc"
            ... ]
            >>> PathHandler.validate_continuous_paths(paths)
            (True, "All paths have matching channels: ['30', '31']")
        """
        if not paths or len(paths) < 2:
            return False, "Need at least 2 paths for continuous validation"

        # 첫 번째 경로의 충방전기 타입 및 채널 확인
        first_cycler_type = detect_cycler_type(paths[0])
        first_channels = get_channel_folders(paths[0], first_cycler_type)

        # 나머지 경로들과 비교
        for path in paths[1:]:
            cycler_type = detect_cycler_type(path)

            # 충방전기 타입 일치 확인
            if cycler_type != first_cycler_type:
                return False, f"Cycler type mismatch: {first_cycler_type.value} vs {cycler_type.value}"

            # 채널명 일치 확인
            channels = get_channel_folders(path, cycler_type)
            if channels != first_channels:
                return False, f"Channel mismatch: {first_channels} vs {channels}"

        return True, f"All paths have matching channels: {first_channels}"

    @staticmethod
    def extract_channel_names(path: str) -> List[str]:
        """
        경로에서 채널명 추출

        Args:
            path: 데이터 폴더 경로

        Returns:
            List[str]: 채널명 리스트

        Example (Toyo):
            >>> PathHandler.extract_channel_names("Rawdata/Q7M...")
            ['30', '31']

        Example (PNE):
            >>> PathHandler.extract_channel_names("Rawdata/A1_MP1...")
            ['M02Ch073[073]', 'M02Ch074[074]']
        """
        cycler_type = detect_cycler_type(path)
        return get_channel_folders(path, cycler_type)

    @staticmethod
    def create_path_group(paths: List[str], validate: bool = True) -> PathGroup:
        """
        경로 그룹 생성

        Args:
            paths: 경로 리스트
            validate: 검증 수행 여부

        Returns:
            PathGroup: 경로 그룹 객체

        Raises:
            ValueError: 검증 실패 시
        """
        if not paths:
            raise ValueError("Empty path list")

        # 충방전기 타입 감지
        cycler_type = detect_cycler_type(paths[0])

        # 채널명 추출
        channel_names = get_channel_folders(paths[0], cycler_type)

        # 검증
        is_validated = False
        if validate and len(paths) > 1:
            success, message = PathHandler.validate_continuous_paths(paths)
            if not success:
                raise ValueError(f"Path validation failed: {message}")
            is_validated = True
        elif len(paths) == 1:
            is_validated = True

        return PathGroup(
            paths=paths,
            cycler_type=cycler_type,
            channel_names=channel_names,
            is_validated=is_validated
        )

    @staticmethod
    def get_lot_and_channel_name(path: str) -> Tuple[str, str]:
        """
        경로에서 LOT명과 채널명 추출

        Args:
            path: 데이터 폴더 경로

        Returns:
            Tuple[str, str]: (LOT명, 채널명)

        Example:
            >>> path = "c:\\data\\LOT123\\Channel01\\"
            >>> PathHandler.get_lot_and_channel_name(path)
            ("LOT123", "Channel01")
        """
        # 경로 정규화
        normalized_path = os.path.normpath(path)

        # 경로 분리
        parts = normalized_path.split(os.sep)

        if len(parts) >= 2:
            lot_name = parts[-2] if len(parts) > 1 else ""
            channel_name = parts[-1]
        else:
            lot_name = ""
            channel_name = parts[-1] if parts else ""

        return lot_name, channel_name

    @staticmethod
    def parse_path_file(filepath: str) -> List[str]:
        """
        경로 파일 파싱 (TSV/TXT 형식)

        Args:
            filepath: 경로 파일 경로

        Returns:
            List[str]: 경로 리스트

        File Format:
            cyclepath    cyclename (optional)
            path/to/data1    Name1
            path/to/data2    Name2
        """
        import pandas as pd

        # TSV 파일 읽기
        df = pd.read_csv(filepath, sep="\t")

        if 'cyclepath' not in df.columns:
            raise ValueError("Path file must contain 'cyclepath' column")

        # 경로 리스트 반환
        return df['cyclepath'].tolist()
