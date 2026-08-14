# `samschema.py` — CSV → SQLite 스키마 자동 구축

`data/` 폴더의 CSV 파일을 읽어 **스키마를 자동으로 추론하고 SQLite 데이터베이스를 통째로 생성하는** 스크립트입니다.
테이블 정의를 사람이 손으로 작성하지 않고, CSV의 컬럼명과 실제 값으로부터 타입 · 기본키 · 외래키 · 생성 순서를 모두 유도해냅니다.

- **입력** — `data/*.csv` (파일명이 곧 테이블명)
- **출력** — 프로젝트 루트의 `cosmetic.db`
- **의존성** — 표준 라이브러리만 (`re`, `csv`, `pathlib`, `sqlite3`)

```bash
python pipeline/samschema.py
```

> **주의** — 실행할 때마다 기존 `cosmetic.db`를 **삭제하고 새로 만듭니다** ([samschema.py:10-11](../pipeline/samschema.py#L10-L11)).
> 항상 같은 결과가 나오는 대신, DB에 직접 넣어둔 데이터가 있다면 함께 지워집니다.

---

## 전체 흐름

```
data/*.csv
   │
   ├─ ① read_csv()            파일별 컬럼명 + 전체 행 읽기
   │
   ├─ ② infer_type()          컬럼별 값을 전부 검사해 타입 결정
   │      └ looks_int / looks_float / looks_date
   │
   ├─ ③ infer_pk()            "_id"로 끝나고 값이 유일한 컬럼 → PK
   │
   ├─ ④ owner_of()            "_id"를 뗀 이름으로 참조 대상 테이블 탐색 → FK
   │
   ├─ ⑤ sort_by_dependency()  부모 테이블이 먼저 오도록 생성 순서 정렬
   │
   └─ ⑥ build_create() → CREATE TABLE
          convert()     → 타입 변환 후 executemany() INSERT
          CREATE INDEX  → 외래키 컬럼에 인덱스
```

②~④의 결과는 `tables` 딕셔너리 한 곳에 모입니다 ([samschema.py:110-136](../pipeline/samschema.py#L110-L136)).

```python
tables["purchases"] = {
    "columns": ["purchase_id", "customer_id", ...],   # 컬럼 순서
    "rows":    [{...}, {...}, ...],                   # CSV 원본 행
    "type":    {"purchase_id": "TEXT", "quantity": "INTEGER", ...},
    "pk":      "purchase_id",
    "fks":     [("customer_id", "customers"), ("product_id", "products")],
}
```

---

## 추론 규칙

### 타입 추론 — `infer_type()`

컬럼의 **빈 문자열을 제외한 모든 값**이 조건을 만족해야 그 타입으로 확정됩니다 (`all()`). 하나라도 어긋나면 다음 후보로 넘어가고, 끝까지 못 맞추면 `TEXT`입니다.

| 순서 | 판별 함수 | 결과 | 규칙 |
|---:|---|---|---|
| 0 | — | `TEXT` | 값이 전부 비어 있는 컬럼 |
| 1 | `looks_int()` | `INTEGER` | 부호(`-`) 제외 전부 숫자. **단 두 자리 이상이면서 `0`으로 시작하면 제외** |
| 2 | `looks_float()` | `FLOAT` | `float()` 변환 성공 **그리고** `.` 포함 |
| 3 | `looks_date()` | `DATE` | 정규표현식 `\d{4}-\d{2}-\d{2}` 완전 일치 |
| 4 | — | `TEXT` | 위 모두 해당 없음 |

`looks_int()`의 "앞자리 0 제외" 규칙이 핵심입니다. 이것 덕분에 `phone` 컬럼의 `01012345678` 같은 값이 정수로 오인되지 않고 `TEXT`로 남습니다 — 정수로 저장하면 앞의 `0`이 사라져 버리기 때문입니다.

`looks_float()`가 `.` 유무를 따로 확인하는 이유도 같습니다. `float("100")`은 성공하므로, 이 검사가 없으면 정수도 실수로 분류됩니다.

### 기본키 추론 — `infer_pk()`

컬럼을 **정의된 순서대로** 훑으며 아래 세 조건을 모두 만족하는 **첫 번째** 컬럼을 PK로 정합니다.

1. 이름이 `_id`로 끝날 것
2. 빈 값이 하나도 없을 것
3. 값이 전부 유일할 것 (`len(set(values)) == len(values)`)

### 외래키 추론 — `owner_of()`

`_id`로 끝나는 컬럼에서 접미사를 떼고, **원형 · `+s` · `+es`** 세 가지 후보로 같은 이름의 테이블을 찾습니다.

```
customer_id → "customer" → "customers" ✓ → customers 테이블 참조
```

찾은 뒤에도 두 가지를 더 확인해야 FK로 인정됩니다 ([samschema.py:128-134](../pipeline/samschema.py#L128-L134)):

- 참조 대상이 **자기 자신이 아닐 것** — 그렇지 않으면 `customers.customer_id`가 자기를 참조하게 됩니다
- 그 컬럼이 **상대 테이블의 실제 PK일 것** — 이름만 같고 키가 아닌 경우를 걸러냅니다

`product_details.product_id`처럼 **PK이면서 동시에 FK**인 경우도 자연스럽게 처리됩니다 (1:1 관계).

### 생성 순서 정렬 — `sort_by_dependency()`

외래키는 참조 대상 테이블이 **먼저 존재해야** 걸 수 있습니다. 이 함수는 위상 정렬(topological sort)로 순서를 정합니다.

- 아직 처리 안 된 테이블 중, **참조하는 부모가 모두 `done`에 들어간** 것을 순서에 추가
- 한 바퀴를 돌았는데 아무것도 추가되지 않으면(`moved == False`) 순환 참조로 보고, 남은 테이블을 전부 뒤에 붙이고 종료

마지막 `if not moved` 분기가 **무한 루프 방지 장치**입니다. 다만 이 경로로 빠지면 FK 제약에 걸릴 수 있으므로, 사실상 "순환 참조는 처리하지 못한다"는 뜻이기도 합니다.

---

## 실제 생성 결과

현재 `data/` 기준으로 다음 순서로 생성됩니다:

```
customers → products → purchases → product_details
```

`purchases`가 `product_details`보다 먼저 오는 것은 알파벳순이 아니라, 첫 번째 순회에서 부모(`customers`, `products`)가 이미 채워진 순간 바로 조건을 만족했기 때문입니다.

| 테이블 | 행 수 | PK | FK |
|---|---:|---|---|
| `customers` | 300 | `customer_id` | — |
| `products` | 200 | `product_id` | — |
| `purchases` | 1,500 | `purchase_id` | `customer_id` → `customers`<br>`product_id` → `products` |
| `product_details` | 200 | `product_id` | `product_id` → `products` |

<details>
<summary>생성되는 DDL 전문</summary>

```sql
CREATE TABLE customers (
   customer_id TEXT PRIMARY KEY,
   name TEXT,
   gender TEXT,
   age INTEGER,
   skin_type TEXT,
   phone TEXT,
   email TEXT,
   city TEXT,
   joined_at DATE
);

CREATE TABLE products (
   product_id TEXT PRIMARY KEY,
   name TEXT,
   brand TEXT,
   category TEXT,
   price INTEGER,
   volume TEXT,
   skin_type TEXT,
   ingredient TEXT,
   concern TEXT,
   tags TEXT,
   description TEXT
);

CREATE TABLE purchases (
   purchase_id TEXT PRIMARY KEY,
   customer_id TEXT,
   product_id TEXT,
   purchased_at DATE,
   quantity INTEGER,
   rating INTEGER,
   review TEXT,
   is_holdout INTEGER,
   FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
   FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE product_details (
   product_id TEXT PRIMARY KEY,
   detail TEXT,
   FOREIGN KEY (product_id) REFERENCES products(product_id)
);
```
</details>

외래키 컬럼에는 인덱스가 자동으로 붙습니다 ([samschema.py:210-211](../pipeline/samschema.py#L210-L211)).

```
idx_purchases_customer_id
idx_purchases_product_id
idx_product_details_product_id
```

SQLite는 PK에는 인덱스를 자동 생성하지만 **FK에는 만들어주지 않습니다.** 조인이 잦은 컬럼이므로 직접 걸어주는 것이 맞습니다.

---

## 데이터 적재

`csv.DictReader`는 모든 값을 **문자열로** 읽습니다. 그래서 추론한 타입에 맞춰 변환한 뒤 넣어야 합니다.

```python
def convert(value, kind):
    if value == "":     return None        # 빈 문자열 → NULL
    if kind == "INTEGER": return int(value)
    if kind == "FLOAT":   return float(value)
    return value                            # TEXT, DATE는 문자열 그대로
```

빈 문자열을 `None`으로 바꾸는 처리가 중요합니다. 이게 없으면 값이 없는 칸이 `""`(빈 문자열)로 저장되어, `IS NULL` 조회에 걸리지 않는 어정쩡한 데이터가 됩니다.

INSERT문은 값을 `?` 플레이스홀더로 바인딩합니다 ([samschema.py:208](../pipeline/samschema.py#L208)).

```python
placeholders = ", ".join("?" for _ in columns)   # 컬럼 8개 → "?, ?, ?, ?, ?, ?, ?, ?"
con.executemany(
    f"INSERT INTO {name} ({", ".join(columns)}) VALUES ({placeholders})",
    values,
)
```

리뷰 텍스트에 작은따옴표가 들어 있어도 안전하고, `executemany`로 한 번에 처리하므로 1,500행도 빠릅니다.

---

## 알아둘 점

### `DATE`는 SQLite의 실제 타입이 아닙니다

SQLite의 저장 클래스는 `NULL / INTEGER / REAL / TEXT / BLOB` 다섯 개뿐입니다. `DATE`라고 선언하면 **NUMERIC 친화도(affinity)** 로 처리되고, `'2025-12-26'`은 숫자로 변환되지 않으므로 결국 **TEXT로 저장**됩니다.

```
declared type : DATE
typeof()      : text
```

`YYYY-MM-DD` 형식은 문자열 정렬 순서와 날짜 순서가 일치하므로 `ORDER BY`나 범위 비교는 정상 동작합니다. 다만 날짜 연산이 필요하면 `date()`, `julianday()` 같은 함수를 써야 합니다.

같은 이유로 `FLOAT`은 문자열에 `FLOA`가 포함되어 **REAL 친화도**를 받으므로 의도대로 동작합니다.

### `PRAGMA foreign_keys`는 연결마다 다시 켜야 합니다

[samschema.py:14](../pipeline/samschema.py#L14)에서 켜지만, 이 설정은 **DB 파일이 아니라 연결(connection)에 붙습니다.** 나중에 다른 스크립트가 `cosmetic.db`에 접속하면 기본값 OFF 상태이므로, 외래키 검증이 필요하면 그쪽에서도 똑같이 실행해야 합니다.

### 테이블명 · 컬럼명은 문자열로 조립됩니다

값은 `?`로 바인딩되지만 테이블명과 컬럼명은 f-string으로 SQL에 직접 들어갑니다. SQL 식별자는 원래 플레이스홀더로 바인딩할 수 없어서 불가피한 방식이며, 여기서는 **입력이 우리가 관리하는 `data/` 폴더의 CSV**라는 전제 위에서 안전합니다. 외부에서 받은 CSV를 넣는다면 파일명과 헤더 검증이 필요합니다.

### 중복 순회와 사용되지 않는 코드

[23-28행](../pipeline/samschema.py#L23-L28)과 [78-82행](../pipeline/samschema.py#L78-L82)의 반복문은 값을 변수에 담기만 하고 **아무 데도 쓰지 않습니다.** 개발 중 확인용으로 `print`를 걸었던 자리로, 지금은 동작에 영향이 없습니다.

다만 이 때문에 각 CSV 파일을 **총 3번** 읽습니다 (23행, 78행, 111행). 현재 규모(약 2,200행)에서는 체감되지 않지만, 데이터가 커지면 두 블록을 지우는 것만으로 실행 시간이 1/3로 줄어듭니다.

### Python 3.12 이상 필요

[208행](../pipeline/samschema.py#L208)의 `f"...{", ".join(columns)}..."`처럼 f-string 안에서 **바깥과 같은 종류의 따옴표**를 쓰는 문법은 Python 3.12(PEP 701)부터 허용됩니다. 낮은 버전을 지원해야 한다면 `col_list = ", ".join(columns)`로 미리 빼두면 됩니다.

### 커밋은 마지막에 한 번

[212행](../pipeline/samschema.py#L212)의 `con.commit()` 하나로 전체가 확정됩니다. 중간에 오류가 나면 아무것도 저장되지 않으므로, DB가 "일부만 채워진" 어중간한 상태로 남지 않습니다.
