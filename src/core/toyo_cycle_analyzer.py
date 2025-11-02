"""
Toyo Cycle Analyzer

Concrete implementation for Toyo cycle data analysis.
Source: BatteryDataTool.py toyo_cycle_data (line 636-751)
"""

import os
import pandas as pd

from .base_cycle_analyzer import BaseCycleAnalyzer
from ..legacy.toyo_functions import toyo_min_cap, toyo_cycle_import
from ..utils.config_models import CycleConfig


class ToyoCycleAnalyzer(BaseCycleAnalyzer):
    """
    Toyo Cycle Data Analyzer

    Analyzes cycle-level performance metrics from Toyo capacity.log files

    Metrics:
    - Charge/Discharge capacity
    - Charge/Discharge efficiency
    - Rest end voltage
    - Discharge energy
    - Temperature
    - Average voltage
    - DCIR (optional)
    """

    def __init__(self, config: CycleConfig):
        super().__init__(config)

    def _calculate_capacity(self) -> float:
        """
        Calculate battery capacity using Toyo method

        Returns:
            float: Capacity in mAh
        """
        return toyo_min_cap(
            self.config.raw_file_path,
            self.config.mincapacity,
            self.config.firstCrate
        )

    def _load_cycle_data(self) -> pd.DataFrame:
        """
        Load Toyo cycle data from capacity.log

        Returns:
            pd.DataFrame: Raw cycle data
        """
        tempdata = toyo_cycle_import(self.config.raw_file_path)

        if hasattr(tempdata, 'dataraw') and not tempdata.dataraw.empty:
            return tempdata.dataraw

        return pd.DataFrame()

    def _calculate_dcir(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate DCIR from individual cycle files

        DCIR = (Vmax - Vmin) / Imax * 1,000,000 (μΩ → mΩ)

        Args:
            df: Processed cycle data

        Returns:
            pd.DataFrame: DCIR data with "dcir" column
        """
        # Find DCIR measurement cycles
        dcir = df[
            ((df["Finish"] == "                 Tim") |
             (df["Finish"] == "Tim") |
             (df["Finish"] == "Time")) &
            (df["Condition"] == 2) &
            (df["Cap[mAh]"] < (self.mincapacity / 60))
        ]

        cycnum = dcir["TotlCycle"]

        # Calculate DCIR for each cycle
        for cycle in cycnum:
            cycle_file = self.config.raw_file_path + "\\%06d" % cycle

            if os.path.isfile(cycle_file):
                dcirpro = pd.read_csv(
                    cycle_file,
                    sep=",",
                    skiprows=3,
                    engine="c",
                    encoding="cp949",
                    on_bad_lines='skip'
                )

                # Handle different column names
                if "PassTime[Sec]" in dcirpro.columns:
                    dcirpro = dcirpro[[
                        "PassTime[Sec]", "Voltage[V]", "Current[mA]",
                        "Condition", "Temp1[Deg]"
                    ]]
                else:
                    dcirpro = dcirpro[[
                        "Passed Time[Sec]", "Voltage[V]", "Current[mA]",
                        "Condition", "Temp1[deg]"
                    ]]
                    dcirpro.columns = [
                        "PassTime[Sec]", "Voltage[V]", "Current[mA]",
                        "Condition", "Temp1[Deg]"
                    ]

                # Calculate DCIR from discharge section
                dcircal = dcirpro[dcirpro["Condition"] == 2]

                if not dcircal.empty:
                    v_max = dcircal["Voltage[V]"].max()
                    v_min = dcircal["Voltage[V]"].min()
                    i_max = round(dcircal["Current[mA]"].max())

                    if i_max != 0:
                        dcir.loc[int(cycle), "dcir"] = (
                            (v_max - v_min) / i_max * 1000000
                        )

        # Create cycle numbering for DCIR
        n = 1
        cyccal = []

        if len(dcir) != 0:
            # Determine DCIR step
            if (len(df[(df["Condition"] == 2)]) / (len(dcir) / 2)) >= 10:
                dcirstep = (int(len(df[(df["Condition"] == 2)]) / (len(dcir) / 2) / 10) + 1) * 10
            else:
                dcirstep = int(len(df[(df["Condition"] == 2)]) / (len(dcir) / 2)) + 1

            for i in range(len(dcir)):
                if self.config.chkir:
                    cyccal.append(n)
                    n = n + 1
                else:
                    cyccal.append(n)
                    if i % 2 == 0:
                        n = n + 1
                    else:
                        n = n + dcirstep - 1

        dcir["Cyc"] = cyccal
        dcir = dcir.set_index(dcir["Cyc"])

        # Return only dcir column
        if "dcir" in dcir.columns:
            return dcir[["dcir"]]

        return pd.DataFrame()
