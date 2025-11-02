"""
공통 유틸리티 함수
BatteryDataTool.py에서 추출 (GUI 의존성 제거)
"""

import os
import re
import bisect
import pandas as pd


def check_cycler(raw_file_path):
    """
    충방전기 타입 판별

    Args:
        raw_file_path: 데이터 폴더 경로

    Returns:
        bool: True=PNE, False=Toyo

    Source: BatteryDataTool.py line 286
    """
    # Pattern 폴더 존재 여부로 판별
    cycler = os.path.isdir(raw_file_path + "\\Pattern")
    return cycler


def convert_steplist(input_str):
    """
    사이클 번호 문자열을 리스트로 변환

    Args:
        input_str: "1-5 10 15" 형식의 문자열

    Returns:
        list: [1, 2, 3, 4, 5, 10, 15]

    Source: BatteryDataTool.py line 292
    """
    output_list = []
    for part in input_str.split():
        if "-" in part:
            start, end = map(int, part.split("-"))
            output_list.extend(range(start, end + 1))
        else:
            output_list.append(int(part))
    return output_list


def same_add(df, column_name):
    """
    중복된 값에 대해 순차적으로 번호 부여

    Args:
        df: DataFrame
        column_name: 처리할 컬럼명

    Returns:
        DataFrame: {column_name}_add 컬럼이 추가된 DataFrame

    Source: BatteryDataTool.py line 303
    """
    new_column_name = f"{column_name}_add"
    df[new_column_name] = df[column_name].apply(lambda x: x)
    # 중복된 값에 대해 1씩 증가
    df[new_column_name] = df.groupby(column_name)[new_column_name].cumcount().add(df[column_name])
    df[new_column_name] = df[new_column_name] - df[new_column_name].min() + 1
    return df


def extract_text_in_brackets(text):
    """
    대괄호 안의 텍스트 추출

    Args:
        text: 입력 문자열

    Returns:
        str: 대괄호 안의 텍스트 (없으면 원본 반환)

    Example:
        "M02Ch073[073]" → "073"
        "Normal Text" → "Normal Text"
    """
    match = re.search(r'\[([^\]]+)\]', text)
    if match:
        return match.group(1)
    return text


def name_capacity(data_file_path):
    """
    파일명에서 용량 값 추출

    Args:
        data_file_path: 파일 경로

    Returns:
        float: 추출된 용량 (mAh), 없으면 None

    Example:
        "path/to/1689mAh_data" → 1689.0
        "path/to/4-5mAh_data" → 4.5

    Source: BatteryDataTool.py line 233
    """
    # 원시 문자열을 사용하여 특수 문자를 공백으로 대체
    raw_file_path = re.sub(r'[._@\$$$$$$\(\)]', ' ', data_file_path)
    # 정규 표현식을 사용하여 "mAh"로 끝나는 용량 값을 찾습니다. (소수점 포함)
    match = re.search(r'(\d+([\-.]\d+)?)mAh', raw_file_path)
    if match:
        # 소수점 용량을 위해 -를 .으로 변환
        min_cap = match.group(1).replace('-', '.')
        return float(min_cap)
    # 용량 값이 없으면 None을 반환
    return None


def binary_search(numbers, target):
    """
    정렬된 리스트에서 타겟 값의 위치 찾기

    Args:
        numbers: 정렬된 숫자 리스트
        target: 찾을 값

    Returns:
        int: 타겟 값이 들어갈 위치 인덱스

    Source: BatteryDataTool.py line 247
    """
    index = bisect.bisect_left(numbers, target)
    return index
