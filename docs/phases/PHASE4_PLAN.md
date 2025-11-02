# Phase 4: Analysis Functions Implementation - Plan

## 📋 목표

Cycle & Profile 분석 기능 구현 및 DB 저장 통합

## 🎯 Phase 4 Overview

### Core Components
1. **Cycle Analyzer**: 사이클별 성능 데이터 분석
2. **Profile Analyzer**: 프로파일 데이터 분석 및 처리
3. **DB Integration**: Loader → Analyzer → DB 파이프라인
4. **Testing**: 실제 데이터로 검증

## 📊 Cycle Analyzer 분석

### Source: `toyo_cycle_data()` (BatteryDataTool.py line 636-751)

**Input**:
- `raw_file_path`: Rawdata 경로
- `mincapacity`: 배터리 용량
- `inirate`: 초기 C-rate
- `chkir`: DCIR 체크 플래그

**Processing Steps**:
1. **Capacity Calculation**: `toyo_min_cap()` 호출
2. **Data Loading**: `toyo_cycle_import()` → Cycleraw
3. **Cycle Adjustment**: 방전 시작 시 사이클 번호 조정
4. **Step Merging**: 연속된 충전/방전 Step 병합
5. **Data Extraction**:
   - 충전 용량 (Chg): Condition == 1
   - 방전 용량 (Dchg): Condition == 2
   - Rest End Voltage (Ocv): 충전 후 OCV
   - 방전 에너지 (DchgEng): Pow[mWh]
   - 평균 전압 (AvgV): Pow/Cap
   - 온도 (Temp): PeakTemp
6. **DCIR Calculation**: 개별 사이클 파일에서 전압/전류 변화 측정
7. **Efficiency Calculation**:
   - 충방효율 (Eff): Dchg / Chg
   - 방충효율 (Eff2): Chg(next) / Dchg
8. **Normalization**: 용량을 mincapacity로 나눔

**Output**:
```python
df.NewData = pd.DataFrame({
    "Dchg": 방전용량 (normalized),
    "RndV": Rest End Voltage,
    "Eff": 충방효율,
    "Chg": 충전용량 (normalized),
    "DchgEng": 방전에너지,
    "Eff2": 방충효율,
    "Temp": 온도,
    "AvgV": 평균전압,
    "OriCyc": 원본 사이클 번호,
    "dcir": DCIR (optional)
})
```

**Return**: `[mincapacity, df]`

### PNE Cycle Analyzer

**Source**: `pne_cycle_data()` (line 1235+)

Similar structure but with PNE-specific:
- SaveEndData.csv 파일 읽기
- 다른 컬럼명 (TotlCycle, chgCap, DchgCap 등)
- DCIR2, RSS OCV/CCV, SOC70 DCIR 추가

## 🏗️ Cycle Analyzer Architecture

### Class Structure

```python
class BaseCycleAnalyzer(ABC):
    """Base class for cycle analysis"""

    def __init__(self, config: CycleConfig):
        self.config = config
        self.mincapacity = 0

    def analyze(self) -> CycleResult:
        """Template method for cycle analysis"""
        self.mincapacity = self._calculate_capacity()
        raw_data = self._load_cycle_data()
        processed_data = self._process_cycles(raw_data)
        result_df = self._calculate_metrics(processed_data)
        return CycleResult(
            mincapacity=self.mincapacity,
            data=result_df,
            metadata=self._get_metadata()
        )

    @abstractmethod
    def _calculate_capacity(self) -> float:
        pass

    @abstractmethod
    def _load_cycle_data(self) -> pd.DataFrame:
        pass

    def _process_cycles(self, df: pd.DataFrame) -> pd.DataFrame:
        """Common cycle processing (merge steps, adjust cycles)"""
        pass

    def _calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate capacity, efficiency, DCIR"""
        pass
```

### Config & Result Models

```python
@dataclass
class CycleConfig:
    raw_file_path: str
    mincapacity: float = 0.0
    inirate: float = 0.2
    chkir: bool = False
    chkir2: bool = False  # PNE only
    mkdcir: bool = False  # PNE only

@dataclass
class CycleResult:
    mincapacity: float
    data: pd.DataFrame  # NewData with all metrics
    metadata: Dict
```

## 📈 Profile Analyzer Architecture

### Already Implemented (Phase 2)
- ✅ `BaseProfileLoader` (Template Method)
- ✅ `ToyoRateProfileLoader`

### To Implement (Phase 4)
- [ ] `ToyoStepProfileLoader` (line 754: toyo_step_Profile_data)
- [ ] `ToyoChargeProfileLoader` (toyo_chg_Profile_data)
- [ ] `ToyoDischargeProfileLoader` (toyo_dchg_Profile_data)
- [ ] `PneRateProfileLoader`
- [ ] `PneStepProfileLoader`

**Note**: Profile Loaders는 Phase 2에서 이미 아키텍처 구축 완료. Phase 4에서는 추가 타입만 구현.

## 🔗 DB Integration Strategy

### Pipeline: Raw Data → Analyzer → DB

```python
# 1. Cycle Analysis
config = CycleConfig(raw_file_path="Rawdata/...", inirate=0.2)
analyzer = ToyoCycleAnalyzer(config)
result = analyzer.analyze()

# 2. DB Storage
with session_scope() as session:
    # Create TestRun
    run_repo = TestRunRepository(session)
    test_run = run_repo.create(
        project_id=project.id,
        raw_file_path=config.raw_file_path,
        cycler_type="TOYO",
        capacity_mah=result.mincapacity
    )

    # Create CycleData (batch)
    cycle_repo = CycleDataRepository(session)
    cycle_data_list = []
    for idx, row in result.data.iterrows():
        cycle_data_list.append({
            "cycle_number": int(row["TotlCycle"]),
            "chg_capacity": row["Chg"] * result.mincapacity,
            "dchg_capacity": row["Dchg"] * result.mincapacity,
            "dchg_energy": row["DchgEng"],
            "efficiency_chg_dchg": row["Eff"] * 100,
            "efficiency_dchg_chg": row["Eff2"] * 100,
            "rest_end_voltage": row["RndV"],
            "avg_voltage": row["AvgV"],
            "temperature": row["Temp"],
            "dcir": row.get("dcir"),
            "original_cycle": int(row["OriCyc"])
        })
    cycle_repo.create_batch(test_run.id, cycle_data_list)

# 3. Profile Analysis & DB Storage
config = ProfileConfig(raw_file_path="Rawdata/...", inicycle=10)
loader = ToyoRateProfileLoader(config)
result = loader.load_profile()

with session_scope() as session:
    # Create ProfileData
    profile_repo = ProfileDataRepository(session)
    profile_data = profile_repo.create(
        test_run_id=test_run.id,
        profile_type="rate",
        cycle_number=config.inicycle,
        cutoff=config.cutoff,
        inirate=config.inirate,
        data_points=len(result.data),
        soc_min=result.data["SOC"].min(),
        soc_max=result.data["SOC"].max()
    )

    # Create ProfileTimeSeries
    ts_repo = ProfileTimeSeriesRepository(session)
    ts_repo.create_from_dataframe(profile_data.id, result.data)
```

## 📁 File Structure (Phase 4)

```
src/
├── core/
│   ├── base_cycle_analyzer.py   # NEW: Base Cycle Analyzer
│   ├── toyo_cycle_analyzer.py   # NEW: Toyo Cycle Analyzer
│   ├── pne_cycle_analyzer.py    # NEW: PNE Cycle Analyzer
│   │
│   ├── toyo_step_loader.py      # NEW: Toyo Step Profile
│   ├── toyo_charge_loader.py    # NEW: Toyo Charge Profile
│   └── toyo_discharge_loader.py # NEW: Toyo Discharge Profile
│
├── utils/
│   └── config_models.py         # UPDATE: Add CycleConfig, CycleResult
│
└── legacy/
    └── toyo_functions.py        # UPDATE: Add toyo_cycle_import

tests/unit/
├── test_toyo_cycle_analyzer.py  # NEW: Cycle analyzer tests
├── test_toyo_step_loader.py     # NEW: Step profile tests
└── test_db_integration.py       # NEW: DB integration tests
```

## 🎯 Implementation Steps

### Step 1: Extract Legacy Cycle Functions
- [ ] `toyo_cycle_import()` → `src/legacy/toyo_functions.py`
- [ ] `pne_cycle_import()` → `src/legacy/pne_functions.py` (new file)

### Step 2: Implement Cycle Analyzer
- [ ] `BaseCycleAnalyzer` (abstract class)
- [ ] `ToyoCycleAnalyzer` (concrete implementation)
- [ ] `CycleConfig`, `CycleResult` models

### Step 3: Implement Additional Profile Loaders
- [ ] `ToyoStepProfileLoader`
- [ ] `ToyoChargeProfileLoader`
- [ ] `ToyoDischargeProfileLoader`

### Step 4: DB Integration
- [ ] Analyzer → DB helper functions
- [ ] Batch processing for large datasets
- [ ] Transaction management

### Step 5: Testing
- [ ] Unit tests for analyzers
- [ ] Integration tests (Analyzer → DB)
- [ ] Real data validation

### Step 6: Documentation
- [ ] PHASE4_SUMMARY.md
- [ ] Update README.md

## 🧪 Testing Strategy

### Unit Tests
1. **Cycle Analyzer Tests**:
   - Capacity calculation
   - Step merging logic
   - Metrics calculation (efficiency, DCIR)
   - Output format validation

2. **Profile Loader Tests**:
   - Step profile loading
   - Charge/discharge profile loading
   - DataFrame output validation

### Integration Tests
1. **DB Integration**:
   - Analyzer → DB 저장
   - Batch insert performance
   - Data retrieval and validation

2. **End-to-End**:
   - Real Rawdata path → Analyzer → DB → Query
   - Legacy comparison (100% match)

## 📊 Success Criteria

- ✅ Cycle Analyzer produces identical output to `toyo_cycle_data()`
- ✅ All metrics calculated correctly (capacity, efficiency, DCIR)
- ✅ DB integration works seamlessly
- ✅ Tests pass with real data
- ✅ Performance: <5s for 400 cycles

## 🔍 Key Design Decisions

### 1. Analyzer vs Loader Separation
- **Analyzer**: Focuses on metrics calculation (cycle-level)
- **Loader**: Focuses on time-series data loading (profile-level)

### 2. Template Method Pattern Reuse
- BaseCycleAnalyzer uses same pattern as BaseProfileLoader
- Consistent architecture across codebase

### 3. Legacy Function Reuse
- `toyo_cycle_import()`, `toyo_min_cap()` reused
- Ensures 100% compatibility

### 4. DB Batch Operations
- Use `create_batch()` for 100+ cycles
- Transaction per TestRun (not per cycle)

## 📝 Notes

**DCIR Calculation Complexity**:
- Requires reading individual cycle files (%06d)
- Voltage/current analysis within discharge pulse
- Optional feature (chkir flag)

**Step Merging Logic**:
- Consecutive steps with same condition merged
- Capacity and energy accumulated
- Critical for accurate cycle metrics

**PNE vs Toyo Differences**:
- Different file formats (SaveEndData.csv vs capacity.log)
- Different column names
- PNE has additional DCIR metrics (RSS, SOC70)
