# Jupyter Notebook 사용 예제

이 디렉토리에는 배터리 데이터 분석 시스템의 Phase별 사용 예제가 포함되어 있습니다.

## 📓 노트북 목록

### 1. [phase1_infrastructure.ipynb](phase1_infrastructure.ipynb)
**Phase 1: 기반 인프라**

- Configuration Models (Pydantic)
- Cycler Detector (자동 장비 타입 감지)
- Path Handler (연속 경로 검증 및 그룹화)

**학습 내용:**
- 타입 안전한 설정 객체 사용
- 자동 장비 감지 및 채널 검색
- 연속 경로 검증 및 그룹화

### 2. [phase2_profile_loader.ipynb](phase2_profile_loader.ipynb)
**Phase 2: Profile Loader**

- BaseProfileLoader (Template Method Pattern)
- ToyoRateProfileLoader (Toyo Rate 테스트)
- 7단계 파이프라인

**학습 내용:**
- Profile 데이터 로드 및 분석
- Rate 성능 테스트 결과 처리
- DataFrame 기반 데이터 분석
- C-rate별 용량 변화 시각화

### 3. [phase3_database.ipynb](phase3_database.ipynb)
**Phase 3: Database 시스템**

- SQLAlchemy ORM Models (5개 테이블)
- Repository Pattern (5개 Repository)
- Session Management
- Pandas DataFrame ↔ Database 변환

**학습 내용:**
- 데이터베이스 초기화 및 테이블 생성
- TestProject, TestRun, CycleData 생성
- 배치 저장 (고성능)
- DataFrame으로 데이터 조회
- Cascade Delete 및 Relationship

### 4. [phase4_cycle_analyzer.ipynb](phase4_cycle_analyzer.ipynb)
**Phase 4: Cycle Analyzer**

- BaseCycleAnalyzer (Template Method Pattern)
- ToyoCycleAnalyzer (Toyo 사이클)
- 5단계 파이프라인
- Database 통합

**학습 내용:**
- 사이클 데이터 분석
- 용량, 효율, 전압, 온도 메트릭
- 데이터베이스에 결과 저장
- 성능 벤치마킹
- DCIR 계산 (선택적)
- 다중 경로 처리

### 5. [phase5_validation.ipynb](phase5_validation.ipynb)
**Phase 5: Legacy Validation**

- BaseLegacyComparator (Template Method Pattern)
- ToyoCycleComparator (Legacy 비교)
- Tolerance-based Validation
- Column-wise Deviation Tracking

**학습 내용:**
- Legacy 코드와 비교 검증
- Tolerance 커스터마이징
- 결과 Export (Dict/JSON)
- 다중 경로 일괄 검증
- Tolerance 민감도 분석

**요구사항:** BatteryDataTool.py 및 pyodbc 모듈

### 6. [complete_workflow.ipynb](complete_workflow.ipynb)
**완전한 워크플로우**

Raw Data → Profile → Cycle → Database → Validation → Visualization

**학습 내용:**
- 전체 파이프라인 실행
- 경로 검증부터 시각화까지
- 성능 메트릭 측정
- 종합 결과 분석

## 🚀 시작하기

### 1. 환경 설정

```bash
# 프로젝트 루트 디렉토리에서
pip install -r requirements.txt

# Jupyter Notebook 설치 (필요시)
pip install jupyter matplotlib
```

### 2. Jupyter Notebook 실행

```bash
# examples 디렉토리에서
cd examples
jupyter notebook
```

또는 프로젝트 루트에서:

```bash
jupyter notebook examples/
```

### 3. 노트북 선택

브라우저에서 Jupyter가 열리면 원하는 Phase의 노트북을 선택합니다.

**권장 순서:**
1. phase1_infrastructure.ipynb (기초)
2. phase2_profile_loader.ipynb (Profile 분석)
3. phase3_database.ipynb (Database)
4. phase4_cycle_analyzer.ipynb (Cycle 분석)
5. phase5_validation.ipynb (검증)
6. complete_workflow.ipynb (통합)

## 📊 테스트 데이터

노트북은 다음 Rawdata 경로를 사용합니다:

### Toyo 연속 경로 (Life Test)
```
Rawdata/250207_250307_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 1-100cyc/30
Rawdata/250219_250319_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 101-200cyc/30
Rawdata/250304_250404_3_김동진_1689mAh_ATL Q7M Inner 2C 상온수명 201-300cyc/30
```

### Toyo 단일 경로 (Rate Test)
```
Rawdata/Q7M Sub ATL [45v 2068mAh] [23] - 250219/30
```

**참고:** 경로가 존재하지 않으면 해당 셀은 자동으로 스킵됩니다.

## 💡 사용 팁

### 셀 실행
- **한 셀 실행:** `Shift + Enter`
- **전체 실행:** `Cell > Run All`
- **실행 중단:** `Kernel > Interrupt`

### 데이터베이스 초기화
각 노트북은 독립적인 SQLite 데이터베이스를 생성합니다:
- phase3_database.ipynb → `battery_demo.db`
- phase4_cycle_analyzer.ipynb → `battery_demo.db`
- complete_workflow.ipynb → `battery_complete.db`

필요시 수동으로 삭제하여 초기화할 수 있습니다.

### 시각화
Matplotlib 그래프가 표시되지 않으면:

```python
%matplotlib inline
```

노트북 상단에 추가합니다.

## 🔍 Phase별 핵심 개념

### Phase 1: 인프라
- **Config Models**: 타입 안전한 설정
- **Cycler Detection**: 자동 장비 감지
- **Path Validation**: 연속 경로 검증

### Phase 2: Profile Loader
- **Template Method**: 7단계 파이프라인
- **Auto Capacity**: 자동 용량 계산
- **DataFrame**: Pandas 통합

### Phase 3: Database
- **ORM Models**: SQLAlchemy 2.0
- **Repository Pattern**: Clean 아키텍처
- **Batch Operations**: 고성능 저장

### Phase 4: Cycle Analyzer
- **Template Method**: 5단계 파이프라인
- **Rich Metrics**: 용량, 효율, 전압, 온도
- **DB Integration**: Repository 패턴

### Phase 5: Validation
- **Tolerance-based**: 물리량별 허용 오차
- **Column-wise**: 8개 컬럼 편차 추적
- **Legacy Compat**: 100% 호환성

### Complete Workflow
- **End-to-End**: 전체 파이프라인
- **Performance**: 벤치마킹
- **Visualization**: 종합 분석

## 📚 추가 자료

- **프로젝트 README**: [../README.md](../README.md)
- **Phase 문서**: [../docs/phases/](../docs/phases/)
- **Production 가이드**: [../docs/PRODUCTION_READINESS.md](../docs/PRODUCTION_READINESS.md)
- **테스트 코드**: [../tests/](../tests/)

## ❓ 문제 해결

### ImportError: No module named 'src'
```python
import sys
sys.path.insert(0, '..')  # 이미 노트북에 포함되어 있음
```

### 경로를 찾을 수 없음
```python
import os
os.path.exists("Rawdata/...")  # 경로 존재 여부 확인
```

### BatteryDataTool.py not found (Phase 5)
```bash
# BatteryDataTool.py를 프로젝트 상위 디렉토리에 배치
# pyodbc 설치
pip install pyodbc
```

## 📝 노트북 수정 및 실험

노트북은 자유롭게 수정하여 실험할 수 있습니다:

- 다른 경로 테스트
- 파라미터 변경 (mincapacity, firstCrate 등)
- 추가 시각화 생성
- 성능 벤치마킹
- 새로운 분석 추가

모든 노트북은 독립적으로 실행 가능하며, 원본 시스템에 영향을 주지 않습니다.

---

**Happy Learning!** 🎓

질문이나 문제가 있으면 프로젝트 README 또는 Phase 문서를 참조하세요.
