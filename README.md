# Cosmetic-Admin

화장품 커머스 데이터를 정제하고 관리하기 위한 데이터 파이프라인 프로젝트입니다.
고객 · 상품 · 구매 이력 CSV를 읽어 스키마를 추론하고 검증하는 단계부터 시작합니다.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-WIP-yellow)
![Dependencies](https://img.shields.io/badge/dependencies-stdlib%20only-lightgrey)
![Last Commit](https://img.shields.io/github/last-commit/inBBong/Cosmetic-Admin)
![Repo Size](https://img.shields.io/github/repo-size/inBBong/Cosmetic-Admin)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## 프로젝트 구조

```
COSMETIC-ADMIN2/
├── data/            # 원본 CSV 데이터
├── pipeline/        # 단계별 전처리 스크립트
│   └── 01_schema.py # 스키마 탐색 및 타입 추론
├── app/             # 애플리케이션 코드
└── doc/             # 문서
```

## 데이터셋

| 파일 | 행 수 | 설명 |
|---|---:|---|
| `customers.csv` | 300 | 고객 정보 (성별, 나이, 피부타입, 지역, 가입일) |
| `products.csv` | 200 | 상품 정보 (브랜드, 카테고리, 가격, 용량, 성분, 태그) |
| `product_details.csv` | 200 | 상품별 상세 설명 (마크다운) |
| `purchases.csv` | 1,500 | 구매 이력 (구매일, 수량, 평점, 리뷰) |

## 파이프라인

### `01_schema.py` — 스키마 탐색

CSV 파일을 순회하며 각 필드의 실제 값을 확인하고, 값의 형태로 타입을 추론합니다.

- `looks_int()` — 정수 판별 (앞자리 `0`은 전화번호로 간주해 제외)
- `looks_float()` — 실수 판별 (소수점 포함 여부 확인)
- `looks_date()` — 날짜 판별 (`YYYY-MM-DD` 정규표현식)

## 실행 방법

```bash
python pipeline/01_schema.py
```

Python 3.12 기준이며, 표준 라이브러리(`csv`, `re`, `pathlib`)만 사용하므로 별도 설치가 필요 없습니다.
