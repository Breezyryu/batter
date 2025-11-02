# Phase 3: Database Design - Battery Data Analysis System

## 📋 Overview

데이터베이스 설계: BatteryDataTool.py의 분석 결과를 저장하고 쿼리 가능하게 구성

**Design Goals**:
1. **Normalization**: 중복 제거, 데이터 무결성 보장
2. **Query Performance**: 인덱스 최적화, 효율적인 조회
3. **Extensibility**: 새로운 분석 타입 추가 용이
4. **Legacy Compatibility**: 기존 데이터 구조와 100% 호환

## 🗃️ Database Schema

### Entity-Relationship Diagram

```
┌─────────────────┐
│   TestProject   │
├─────────────────┤
│ id (PK)         │
│ name            │
│ description     │
│ created_at      │
│ updated_at      │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐
│   TestRun       │
├─────────────────┤
│ id (PK)         │
│ project_id (FK) │
│ raw_file_path   │
│ cycler_type     │ (TOYO/PNE)
│ capacity_mah    │
│ created_at      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
  1:N       1:N
    │         │
    ▼         ▼
┌─────────┐ ┌──────────────┐
│  Cycle  │ │   Profile    │
│  Data   │ │   Data       │
└─────────┘ └──────────────┘
```

### 1. TestProject (프로젝트)

**목적**: 배터리 테스트 프로젝트 그룹화

```sql
CREATE TABLE test_projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL UNIQUE,
    description     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Columns**:
- `id`: Primary Key
- `name`: 프로젝트 이름 (예: "ATL Q7M Inner 2C 상온수명")
- `description`: 프로젝트 설명
- `created_at`, `updated_at`: 생성/수정 시간

### 2. TestRun (테스트 실행)

**목적**: 개별 테스트 실행 정보 (경로, 장비 타입, 용량)

```sql
CREATE TABLE test_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER REFERENCES test_projects(id) ON DELETE CASCADE,
    raw_file_path   TEXT NOT NULL,
    channel_name    TEXT,
    cycler_type     TEXT CHECK(cycler_type IN ('TOYO', 'PNE')),
    capacity_mah    REAL,
    cycle_range_start INTEGER,
    cycle_range_end   INTEGER,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(raw_file_path, channel_name)
);

CREATE INDEX idx_test_runs_project ON test_runs(project_id);
CREATE INDEX idx_test_runs_cycler ON test_runs(cycler_type);
```

**Columns**:
- `id`: Primary Key
- `project_id`: TestProject FK
- `raw_file_path`: Rawdata 경로
- `channel_name`: 채널 이름 (예: "30", "M02Ch073[073]")
- `cycler_type`: 장비 타입 (TOYO/PNE)
- `capacity_mah`: 배터리 용량
- `cycle_range_start/end`: 사이클 범위 (연속 경로용)

### 3. CycleData (사이클 데이터)

**목적**: 사이클별 성능 데이터 (용량, 효율, DCIR 등)

```sql
CREATE TABLE cycle_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id     INTEGER NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    cycle_number    INTEGER NOT NULL,
    original_cycle  INTEGER,

    -- 용량 데이터
    chg_capacity    REAL,  -- 충전 용량 (mAh)
    dchg_capacity   REAL,  -- 방전 용량 (mAh)
    dchg_energy     REAL,  -- 방전 에너지 (Wh)

    -- 효율 데이터
    efficiency_chg_dchg REAL,  -- 충방효율 (%)
    efficiency_dchg_chg REAL,  -- 방충효율 (%)

    -- 전압 데이터
    rest_end_voltage REAL,  -- Rest End 전압 (V)
    ocv              REAL,  -- OCV (V)
    avg_voltage      REAL,  -- 평균 전압 (V)

    -- DCIR 데이터
    dcir             REAL,  -- DCIR (mΩ)
    dcir2            REAL,  -- DCIR2 (mΩ, PNE 전용)
    rss_ocv          REAL,  -- RSS OCV (V)
    rss_ccv          REAL,  -- RSS CCV (V)
    soc70_dcir       REAL,  -- SOC 70% DCIR (mΩ)
    soc70_rss_dcir   REAL,  -- SOC 70% RSS DCIR (mΩ)

    -- 메타데이터
    temperature      REAL,  -- 온도 (℃)
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(test_run_id, cycle_number)
);

CREATE INDEX idx_cycle_data_test_run ON cycle_data(test_run_id);
CREATE INDEX idx_cycle_data_cycle_num ON cycle_data(cycle_number);
CREATE INDEX idx_cycle_data_capacity ON cycle_data(dchg_capacity);
```

**Columns** (from BatteryDataTool.py line 8273-8295):
- **Capacity**: 충전용량, 방전용량, 방전Energy
- **Efficiency**: 충방효율, 방충효율
- **Voltage**: Rest End, OCV, 평균전압
- **DCIR**: dcir, dcir2, rssocv, rssccv, soc70_dcir, soc70_rss_dcir

### 4. ProfileData (프로파일 데이터)

**목적**: Rate/Step/Charge/Discharge 프로파일 분석 결과

```sql
CREATE TABLE profile_data (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_run_id     INTEGER NOT NULL REFERENCES test_runs(id) ON DELETE CASCADE,
    profile_type    TEXT NOT NULL CHECK(profile_type IN ('rate', 'step', 'charge', 'discharge', 'continue', 'dcir')),
    cycle_number    INTEGER NOT NULL,

    -- Profile Config
    cutoff          REAL,
    inirate         REAL,
    smoothdegree    INTEGER,

    -- 분석 결과 메타데이터
    data_points     INTEGER,  -- 데이터 포인트 수
    soc_min         REAL,     -- SOC 최소값
    soc_max         REAL,     -- SOC 최대값

    -- JSON으로 저장될 상세 데이터 경로
    data_file_path  TEXT,     -- CSV 또는 Parquet 파일 경로

    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    UNIQUE(test_run_id, profile_type, cycle_number)
);

CREATE INDEX idx_profile_data_test_run ON profile_data(test_run_id);
CREATE INDEX idx_profile_data_type ON profile_data(profile_type);
CREATE INDEX idx_profile_data_cycle ON profile_data(cycle_number);
```

**Columns**:
- `profile_type`: 프로파일 종류 (rate, step, charge, discharge, continue, dcir)
- `cycle_number`: 사이클 번호
- `cutoff`, `inirate`, `smoothdegree`: 분석 설정
- `data_points`, `soc_min`, `soc_max`: 메타데이터
- `data_file_path`: 상세 시계열 데이터 파일 경로 (TimeMin, SOC, Vol, Crate, Temp)

### 5. ProfileTimeSeries (프로파일 시계열 데이터)

**목적**: Profile의 상세 시계열 데이터 (TimeMin, SOC, Vol, Crate, Temp)

```sql
CREATE TABLE profile_timeseries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id      INTEGER NOT NULL REFERENCES profile_data(id) ON DELETE CASCADE,

    -- 시계열 데이터 (Phase 2 출력 형식)
    time_min        REAL NOT NULL,  -- 시간 (분)
    soc             REAL NOT NULL,  -- State of Charge (0~1)
    voltage         REAL NOT NULL,  -- 전압 (V)
    crate           REAL NOT NULL,  -- C-rate
    temperature     REAL,           -- 온도 (℃)

    -- 추가 분석 데이터 (옵션)
    dqdv            REAL,           -- dQ/dV (mAh/V)

    UNIQUE(profile_id, time_min)
);

CREATE INDEX idx_profile_ts_profile ON profile_timeseries(profile_id);
CREATE INDEX idx_profile_ts_soc ON profile_timeseries(soc);
```

**Note**: 대용량 시계열 데이터의 경우 별도 Parquet 파일로 저장하고 `profile_data.data_file_path`에 경로만 기록하는 방식도 고려

## 🔑 Key Design Decisions

### 1. Normalization Strategy

**3NF (Third Normal Form)** 적용:
- TestProject → TestRun → CycleData/ProfileData
- 중복 제거, 데이터 무결성 보장
- 쿼리 성능과 정규화 균형

### 2. Time Series Data Storage

**Hybrid Approach**:
- **Metadata**: DB에 저장 (profile_data 테이블)
- **Time Series**: 파일 시스템에 Parquet 저장 (profile_data.data_file_path)
- **Alternative**: profile_timeseries 테이블에 직접 저장

**Trade-offs**:
| 방식 | 장점 | 단점 |
|------|------|------|
| DB 저장 | SQL 쿼리 가능, 트랜잭션 지원 | 대용량 시 느림 |
| 파일 저장 | 대용량 처리 빠름, 압축 효율 | 쿼리 불편, 동기화 필요 |
| Hybrid | 메타는 쿼리, 데이터는 빠름 | 복잡도 증가 |

**Phase 3 선택**: DB 저장 → 구현 단순, 쿼리 편의성

### 3. Indexing Strategy

**Primary Indexes**:
- `test_runs(project_id)`: 프로젝트별 조회
- `cycle_data(test_run_id, cycle_number)`: 사이클 데이터 조회
- `profile_data(test_run_id, profile_type)`: 프로파일 타입별 조회

**Performance Indexes**:
- `cycle_data(dchg_capacity)`: 용량 기반 필터링
- `profile_timeseries(soc)`: SOC 범위 조회

### 4. Data Types

- **REAL**: 모든 측정값 (float64 호환)
- **INTEGER**: ID, cycle_number, data_points
- **TEXT**: 경로, 이름, enum 값
- **DATETIME**: 타임스탬프 (ISO 8601 format)

### 5. Constraints

- **Foreign Keys**: ON DELETE CASCADE (부모 삭제 시 자식도 삭제)
- **UNIQUE**: 중복 방지 (raw_file_path + channel_name, test_run_id + cycle_number)
- **CHECK**: Enum 값 검증 (cycler_type, profile_type)
- **NOT NULL**: 필수 필드 강제

## 📊 Query Examples

### Example 1: 프로젝트별 모든 사이클 데이터 조회

```sql
SELECT
    tr.raw_file_path,
    tr.channel_name,
    cd.cycle_number,
    cd.dchg_capacity,
    cd.efficiency_chg_dchg,
    cd.dcir
FROM cycle_data cd
JOIN test_runs tr ON cd.test_run_id = tr.id
JOIN test_projects tp ON tr.project_id = tp.id
WHERE tp.name = 'ATL Q7M Inner 2C 상온수명'
ORDER BY tr.id, cd.cycle_number;
```

### Example 2: Rate Profile 메타데이터 조회

```sql
SELECT
    tr.raw_file_path,
    pd.cycle_number,
    pd.data_points,
    pd.soc_min,
    pd.soc_max,
    pd.cutoff,
    pd.inirate
FROM profile_data pd
JOIN test_runs tr ON pd.test_run_id = tr.id
WHERE pd.profile_type = 'rate'
  AND tr.cycler_type = 'TOYO'
ORDER BY pd.cycle_number;
```

### Example 3: Profile 시계열 데이터 조회

```sql
SELECT
    pts.time_min,
    pts.soc,
    pts.voltage,
    pts.crate,
    pts.temperature
FROM profile_timeseries pts
JOIN profile_data pd ON pts.profile_id = pd.id
WHERE pd.id = 1
ORDER BY pts.time_min;
```

### Example 4: 용량 감소 트렌드 분석

```sql
SELECT
    cycle_number,
    AVG(dchg_capacity) as avg_capacity,
    MIN(dchg_capacity) as min_capacity,
    MAX(dchg_capacity) as max_capacity
FROM cycle_data
WHERE test_run_id = 1
GROUP BY cycle_number
ORDER BY cycle_number;
```

## 🔧 Technology Stack

### Database Engine
- **SQLite**: 단순, 파일 기반, 설치 불필요
- **PostgreSQL (Future)**: 대용량, 고성능, 동시성 지원

### ORM
- **SQLAlchemy**: Python 표준 ORM
- **Alembic**: 마이그레이션 관리

### Data Files
- **Parquet**: 컬럼형 저장, 압축 효율, Pandas 호환

## 📁 File Structure (Phase 3)

```
src/
├── database/
│   ├── __init__.py
│   ├── models.py          # SQLAlchemy ORM 모델
│   ├── session.py         # DB 세션 관리
│   └── repository.py      # Repository 패턴
│
├── core/
│   └── db_manager.py      # DB 관리 헬퍼
│
└── config/
    └── database.yaml      # DB 설정

tests/
└── unit/
    ├── test_models.py     # ORM 모델 테스트
    └── test_repository.py # Repository 테스트

data/
└── profile_files/         # Parquet 파일 저장 (옵션)
```

## 🎯 Implementation Plan

### Step 1: SQLAlchemy Models
- TestProject, TestRun, CycleData, ProfileData, ProfileTimeSeries
- Relationships, Constraints, Indexes

### Step 2: Database Session Management
- Engine 설정, Session factory
- Context manager for transactions

### Step 3: Repository Pattern
- CRUD operations
- Query helpers
- Batch operations

### Step 4: Integration with Loaders
- ProfileLoader → DB 저장
- CycleAnalyzer → DB 저장

### Step 5: Testing
- Unit tests for models
- Integration tests with real data
- Migration tests

## 🔍 Validation Strategy

### 1. Data Integrity
- Foreign key constraints 검증
- Unique constraint 검증
- NOT NULL constraint 검증

### 2. Query Performance
- 인덱스 효과 측정 (EXPLAIN QUERY PLAN)
- 대용량 데이터 삽입 성능 테스트
- 쿼리 응답 시간 측정

### 3. Legacy Compatibility
- BatteryDataTool.py 출력과 DB 데이터 비교
- Excel 출력과 DB 쿼리 결과 비교
- 100% 일치 검증

## 📝 Next Steps

1. **SQLAlchemy Models 구현** (`src/database/models.py`)
2. **DB Session 관리** (`src/database/session.py`)
3. **Repository 패턴 구현** (`src/database/repository.py`)
4. **단위 테스트 작성** (`tests/unit/test_models.py`)
5. **통합 테스트** (실제 데이터로 DB 저장 및 조회)
