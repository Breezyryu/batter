# Phase 0: Legacy 함수 추출 및 기준 데이터 생성

## 📋 목표
BatteryDataTool.py에서 핵심 공통 함수 추출 및 프로젝트 구조 생성

## ✅ 완료 항목

### 1. 프로젝트 구조 생성
```
battery251027/
├── src/
│   ├── core/
│   ├── analysis/
│   ├── database/
│   ├── utils/
│   └── legacy/          # Legacy 함수 저장
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── validation/
│   └── fixtures/
├── validation/
│   └── reports/
└── config/
```

### 2. 공통 함수 추출 (`src/legacy/common_functions.py`)

| 함수명 | 원본 위치 | 설명 |
|--------|-----------|------|
| `check_cycler()` | line 286 | Pattern 폴더로 PNE/Toyo 구분 |
| `convert_steplist()` | line 292 | "1-5 10" → [1,2,3,4,5,10] 변환 |
| `same_add()` | line 303 | 중복 값에 순차 번호 부여 |
| `extract_text_in_brackets()` | - | 대괄호 안 텍스트 추출 |
| `name_capacity()` | line 233 | 파일명에서 용량 추출 |
| `binary_search()` | line 247 | 이진 탐색 |

### 3. Dependencies 설정
- `requirements.txt` 작성
- 핵심 라이브러리: pandas, numpy, sqlalchemy, pytest

## 📦 생성 파일

```
src/
├── __init__.py
├── legacy/
│   ├── __init__.py
│   └── common_functions.py    ✅ 6개 함수 추출
├── core/
│   └── __init__.py
└── utils/
    └── __init__.py

requirements.txt                ✅ 의존성 정의
```

## 🎯 다음 단계
Phase 1에서 Config 모델, Cycler Detector, Path Handler 구현
