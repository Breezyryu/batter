"""
배터리 충방전기 타입 자동 감지 모듈
"""

import os
from ..utils.config_models import CyclerType


def detect_cycler_type(path: str) -> CyclerType:
    """
    데이터 경로에서 충방전기 타입 자동 감지

    Detection Logic:
        - Pattern 폴더 존재 → PNE
        - Pattern 폴더 없음 → Toyo

    Args:
        path: 데이터 폴더 경로

    Returns:
        CyclerType: TOYO 또는 PNE

    Example:
        >>> detect_cycler_type("Rawdata/A1_MP1_4500mAh_T23_1")
        CyclerType.PNE

        >>> detect_cycler_type("Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219r")
        CyclerType.TOYO
    """
    pattern_folder = os.path.join(path, "Pattern")

    if os.path.isdir(pattern_folder):
        return CyclerType.PNE
    else:
        return CyclerType.TOYO


def validate_path_exists(path: str) -> bool:
    """
    경로 존재 여부 확인

    Args:
        path: 확인할 경로

    Returns:
        bool: 경로가 존재하면 True

    Raises:
        FileNotFoundError: 경로가 존재하지 않으면 예외 발생
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Path does not exist: {path}")

    if not os.path.isdir(path):
        raise NotADirectoryError(f"Path is not a directory: {path}")

    return True


def get_channel_folders(path: str, cycler_type: CyclerType) -> list:
    """
    데이터 경로에서 채널 폴더 리스트 추출

    Args:
        path: 데이터 폴더 경로
        cycler_type: 충방전기 타입

    Returns:
        list: 채널 폴더명 리스트

    Example (Toyo):
        >>> get_channel_folders("Rawdata/Q7M...", CyclerType.TOYO)
        ['10', '11', '12', ...]

    Example (PNE):
        >>> get_channel_folders("Rawdata/A1_MP1...", CyclerType.PNE)
        ['M02Ch073[073]', 'M02Ch074[074]']
    """
    validate_path_exists(path)

    # 하위 폴더 리스트
    subfolders = [
        f for f in os.listdir(path)
        if os.path.isdir(os.path.join(path, f))
    ]

    # Pattern 폴더 제외
    channel_folders = [f for f in subfolders if f != "Pattern"]

    # Toyo의 경우 숫자 폴더만 추출
    if cycler_type == CyclerType.TOYO:
        channel_folders = [f for f in channel_folders if f.isdigit()]
        # 숫자 순으로 정렬
        channel_folders.sort(key=int)
    else:
        # PNE의 경우 알파벳 순 정렬
        channel_folders.sort()

    return channel_folders
