"""
Toyo 충방전기 관련 함수
BatteryDataTool.py에서 추출
"""

import os
import pandas as pd
from .common_functions import name_capacity


def toyo_read_csv(*args):
    """
    Toyo CSV 파일 읽기

    Args:
        *args: (filepath) 또는 (filepath, cycle_number)

    Returns:
        pd.DataFrame: 읽은 데이터

    Source: BatteryDataTool.py line 574
    """
    if len(args) == 1:
        filepath = args[0] + "\\capacity.log"
        skiprows = 0
    else:
        filepath = args[0] + "\\%06d" % args[1]
        skiprows = 3

    if os.path.isfile(filepath):
        dataraw = pd.read_csv(
            filepath,
            sep=",",
            skiprows=skiprows,
            engine="c",
            encoding="cp949",
            on_bad_lines='skip'
        )
        return dataraw

    return pd.DataFrame()


def toyo_Profile_import(raw_file_path, cycle):
    """
    Toyo Profile 데이터 불러오기

    Args:
        raw_file_path: 데이터 폴더 경로
        cycle: 사이클 번호

    Returns:
        DataFrame with dataraw attribute

    Source: BatteryDataTool.py line 588
    """
    df = pd.DataFrame()
    df.dataraw = toyo_read_csv(raw_file_path, cycle)

    if hasattr(df, 'dataraw') and not df.dataraw.empty:
        if "PassTime[Sec]" in df.dataraw.columns:
            if "Temp1[Deg]" in df.dataraw.columns:
                # Toyo BLK 3600_3000
                df.dataraw = df.dataraw[["PassTime[Sec]", "Voltage[V]", "Current[mA]", "Condition", "Temp1[Deg]"]]
            else:
                # 신뢰성 충방전기 (Temp 없음)
                df.dataraw = df.dataraw[["PassTime[Sec]", "Voltage[V]", "Current[mA]", "Condition", "TotlCycle"]]
                df.dataraw.columns = ["PassTime[Sec]", "Voltage[V]", "Current[mA]", "Condition", "Temp1[Deg]"]
        else:
            # Toyo BLK5200
            df.dataraw = df.dataraw[["Passed Time[Sec]", "Voltage[V]", "Current[mA]", "Condition", "Temp1[deg]"]]
            df.dataraw.columns = ["PassTime[Sec]", "Voltage[V]", "Current[mA]", "Condition", "Temp1[Deg]"]

    return df


def toyo_cycle_import(raw_file_path):
    """
    Toyo Cycle 데이터 불러오기 (capacity.log)

    Args:
        raw_file_path: 데이터 폴더 경로

    Returns:
        DataFrame with dataraw attribute containing cycle summary data

    Source: BatteryDataTool.py line 608
    """
    df = pd.DataFrame()
    df.dataraw = toyo_read_csv(raw_file_path)

    if hasattr(df, 'dataraw') and not df.dataraw.empty:
        if "Cap[mAh]" in df.dataraw.columns:
            # Standard column names
            df.dataraw = df.dataraw[[
                "TotlCycle", "Condition", "Cap[mAh]", "Ocv", "Finish", "Mode",
                "PeakVolt[V]", "Pow[mWh]", "PeakTemp[Deg]", "AveVolt[V]"
            ]]
        else:
            # Alternative column names (older Toyo format)
            df.dataraw = df.dataraw[[
                "Total Cycle", "Condition", "Capacity[mAh]", "OCV[V]", "End Factor", "Mode",
                "Peak Volt.[V]", "Power[mWh]", "Peak Temp.[deg]", "Ave. Volt.[V]"
            ]]
            df.dataraw.columns = [
                "TotlCycle", "Condition", "Cap[mAh]", "Ocv", "Finish", "Mode",
                "PeakVolt[V]", "Pow[mWh]", "PeakTemp[Deg]", "AveVolt[V]"
            ]

    return df


def toyo_min_cap(raw_file_path, mincapacity, inirate):
    """
    Toyo 최소 용량 산정

    Args:
        raw_file_path: 데이터 폴더 경로
        mincapacity: 지정 용량 (0이면 자동 계산)
        inirate: 초기 C-rate (기본 0.2C)

    Returns:
        float: 계산된 용량 (mAh)

    Source: BatteryDataTool.py line 623
    """
    if mincapacity == 0:
        if "mAh" in raw_file_path:
            # 파일 이름에서 용량 추출
            mincap = name_capacity(raw_file_path)
        else:
            # 첫 사이클 전류로 계산
            inicapraw = toyo_read_csv(raw_file_path, 1)
            if not inicapraw.empty and "Current[mA]" in inicapraw.columns:
                mincap = int(round(inicapraw["Current[mA]"].max() / inirate))
            else:
                mincap = 0
    else:
        mincap = mincapacity

    return mincap
