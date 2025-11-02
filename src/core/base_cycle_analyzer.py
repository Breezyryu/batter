"""
Base Cycle Analyzer - Template Method Pattern

Abstract base class for battery cycle data analysis.
Provides common pipeline for extracting cycle-level metrics.
"""

from abc import ABC, abstractmethod
from typing import Dict
import pandas as pd

from ..utils.config_models import CycleConfig, CycleResult


class BaseCycleAnalyzer(ABC):
    """
    Base class for cycle data analysis

    Template Method Pattern:
    1. Calculate Capacity
    2. Load Cycle Data
    3. Process Cycles (merge steps, adjust numbers)
    4. Calculate Metrics (capacity, efficiency, DCIR)
    5. Format Output
    """

    def __init__(self, config: CycleConfig):
        """
        Initialize cycle analyzer

        Args:
            config: CycleConfig with analysis parameters
        """
        self.config = config
        self.mincapacity = 0.0

    def analyze(self) -> CycleResult:
        """
        Main analysis pipeline (Template Method)

        Returns:
            CycleResult with mincapacity and cycle metrics DataFrame
        """
        # Step 1: Calculate capacity
        self.mincapacity = self._calculate_capacity()

        # Step 2: Load raw cycle data
        raw_data = self._load_cycle_data()

        if raw_data.empty:
            return CycleResult(
                mincapacity=self.mincapacity,
                data=pd.DataFrame(),
                metadata=self._get_metadata()
            )

        # Step 3: Process cycles (adjust, merge steps)
        processed_data = self._process_cycles(raw_data)

        # Step 4: Calculate metrics (capacity, efficiency, DCIR)
        metrics_data = self._calculate_metrics(processed_data)

        # Step 5: Format output
        final_data = self._format_output(metrics_data)

        return CycleResult(
            mincapacity=self.mincapacity,
            data=final_data,
            metadata=self._get_metadata()
        )

    @abstractmethod
    def _calculate_capacity(self) -> float:
        """
        Calculate battery capacity

        Returns:
            float: Capacity in mAh
        """
        pass

    @abstractmethod
    def _load_cycle_data(self) -> pd.DataFrame:
        """
        Load raw cycle data from files

        Returns:
            pd.DataFrame: Raw cycle data
        """
        pass

    def _process_cycles(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process cycle data (common logic)

        Steps:
        1. Save original cycle numbers
        2. Adjust cycle numbers if starting with discharge
        3. Merge consecutive steps with same condition

        Args:
            df: Raw cycle data

        Returns:
            pd.DataFrame: Processed cycle data
        """
        # Make a copy to avoid modifying original
        df = df.copy()

        # Step 1: Save original cycle numbers
        df.loc[:, "OriCycle"] = df.loc[:, "TotlCycle"]

        # Step 2: Adjust cycle numbers if discharge-first
        if df.loc[0, "Condition"] == 2 and len(df.index) > 2:
            if df.loc[1, "TotlCycle"] == 1:
                df.loc[df["Condition"] == 2, "TotlCycle"] -= 1
                df = df.drop(0, axis=0)
                df = df.reset_index(drop=True)

        # Step 3: Merge consecutive steps with same condition
        df = self._merge_consecutive_steps(df)

        return df

    def _merge_consecutive_steps(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge consecutive steps with same condition

        Combines capacity and energy for charge/discharge steps

        Args:
            df: Cycle data

        Returns:
            pd.DataFrame: Data with merged steps
        """
        i = 0
        while i < len(df) - 1:
            current_cond = df.loc[i, "Condition"]
            next_cond = df.loc[i + 1, "Condition"]

            if current_cond in (1, 2) and current_cond == next_cond:
                # Merge steps
                if current_cond == 1:
                    # Charge: accumulate capacity, keep first OCV
                    df.loc[i + 1, "Cap[mAh]"] += df.loc[i, "Cap[mAh]"]
                    df.loc[i + 1, "Ocv"] = df.loc[i, "Ocv"]
                else:
                    # Discharge: accumulate capacity and energy
                    df.loc[i + 1, "Cap[mAh]"] += df.loc[i, "Cap[mAh]"]
                    df.loc[i + 1, "Pow[mWh]"] += df.loc[i, "Pow[mWh]"]
                    df.loc[i + 1, "AveVolt[V]"] = (
                        df.loc[i + 1, "Pow[mWh]"] / df.loc[i + 1, "Cap[mAh]"]
                    )

                # Drop merged row and reset index
                df = df.drop(i, axis=0).reset_index(drop=True)
            else:
                i += 1

        return df

    def _calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate cycle metrics (common logic)

        Metrics:
        - Charge capacity (Chg)
        - Discharge capacity (Dchg)
        - Discharge energy (DchgEng)
        - Rest end voltage (RndV)
        - Efficiencies (Eff, Eff2)
        - Temperature (Temp)
        - Average voltage (AvgV)
        - DCIR (optional)

        Args:
            df: Processed cycle data

        Returns:
            pd.DataFrame: Metrics data
        """
        # Set index to cycle number
        df.index = df["TotlCycle"]

        # Extract charge capacity
        chgdata = df[
            (df["Condition"] == 1) &
            (df["Finish"] != "                 Vol") &
            (df["Finish"] != "Volt") &
            (df["Cap[mAh]"] > (self.mincapacity / 60))
        ]
        chgdata.index = chgdata["TotlCycle"]
        Chg = chgdata["Cap[mAh]"]
        Ocv = chgdata["Ocv"]

        # Extract discharge data
        Dchgdata = df[
            (df["Condition"] == 2) &
            (df["Cap[mAh]"] > (self.mincapacity / 60))
        ]
        Dchg = Dchgdata["Cap[mAh]"]
        Temp = Dchgdata["PeakTemp[Deg]"]
        DchgEng = Dchgdata["Pow[mWh]"]
        AvgV = Dchgdata["AveVolt[V]"]
        OriCycle = Dchgdata.loc[:, "OriCycle"]

        # Calculate efficiencies
        Chg2 = Chg.shift(periods=-1)
        Eff = Dchg / Chg
        Eff2 = Chg2 / Dchg

        # Normalize capacity
        Dchg_norm = Dchg / self.mincapacity
        Chg_norm = Chg / self.mincapacity

        # Combine into result DataFrame
        result_df = pd.DataFrame({
            "Dchg": Dchg_norm,
            "RndV": Ocv,
            "Eff": Eff,
            "Chg": Chg_norm,
            "DchgEng": DchgEng,
            "Eff2": Eff2,
            "Temp": Temp,
            "AvgV": AvgV,
            "OriCyc": OriCycle
        })

        # Calculate DCIR if enabled
        if self.config.chkir:
            dcir_data = self._calculate_dcir(df)
            if dcir_data is not None and not dcir_data.empty:
                result_df = pd.concat([result_df, dcir_data], axis=1, join="outer")

        return result_df

    @abstractmethod
    def _calculate_dcir(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate DCIR (equipment-specific)

        Args:
            df: Processed cycle data

        Returns:
            pd.DataFrame: DCIR data
        """
        pass

    def _format_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Format final output DataFrame

        Args:
            df: Metrics data

        Returns:
            pd.DataFrame: Formatted output
        """
        # Drop rows with no discharge capacity
        df = df.dropna(axis=0, how='all', subset=['Dchg'])

        # Reset index
        df = df.reset_index()

        # Drop TotlCycle column if exists
        if "TotlCycle" in df.columns:
            df = df.drop("TotlCycle", axis=1)

        return df

    def _get_metadata(self) -> Dict:
        """
        Get analysis metadata

        Returns:
            Dict: Metadata
        """
        return {
            "vendor": self.__class__.__name__,
            "capacity_mah": self.mincapacity,
            "firstCrate": self.config.firstCrate,
            "chkir": self.config.chkir,
            "raw_file_path": self.config.raw_file_path
        }
