import re
import csv
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
db_file = ROOT / "cosmetic.db"

if db_file.exists():
  db_file.unlink()

con = sqlite3.connect(db_file)
con.execute("PRAGMA foreign_keys = ON")

# csv파일 내용 리스트 변환 함수
def read_csv(path):
  with open(path, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    return reader.fieldnames, list(reader)

# csv-레코드 정렬
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)

  # 각 csv파일의 첫번째의 모든 필드값 확인
  for column in columns:
    value = rows[0][column]


# 해당 값이 정수인지 확인하는 함수
def looks_int(text):  
  body = text[1:] if text.startswith("-") else text

  if not body.isdigit():      
    return False  
  return not (len(body) > 1 and body.startswith("0"))


# 소수 판별 함수
def looks_float(text):  
  try:
    float(text)
  
  except ValueError:
    return False
  
  if "." not in text:
      return False

  return True


# 날짜 판별 함수
def looks_date(text):
  return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None

# 타입 추론 함수 생성
def infer_type(values):
  seen = [v for v in values if v!=""]

  if not seen: 
    return "TEXT"

  if all(looks_int(v) for v in seen):
    return "INTEGER"

  if all(looks_float(v) for v in seen):
    return "FLOAT"

  if all(looks_date(v) for v in seen):
    return "DATE"

  return "TEXT"


# 모든 csv파일을 하나씩 검사해서 컬럼명과 각 행의 값의 타입을 분석
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)

  for column in columns:
    kind = infer_type([r[column]  for r in rows]) 


# PK를 찾아주는 함수
def infer_pk(columns, rows):
  for col in columns:
    if not col.endswith("_id"):
      continue
  
    values = [r[col] for r in rows]
    if "" in values: 
      continue
   
    if len(set(values)) == len(values):
      return col
  return None

# 특정 PK의 주인 테이블 찾기
def owner_of(column, tables):  
  stem = column[:-3]
  for candidate in (stem, stem+"s", stem+"es") :
    if candidate in tables:
      return candidate

  return None


# 1.모든 테이블별 필드, 데이터타입, PK 구하기
tables = {}
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)
  tables[path.stem] = {
    "columns": columns,
    "rows":rows,
    "type": {col: infer_type([r[col] for r in rows]) for col in columns},
    "pk":infer_pk(columns, rows)
  }

# 2. 특정 테이블에 연결되어 있는 외래키 찾기
for name, table in tables.items(): 
  fks = []
  for col in table["columns"]:
    if not col.endswith("_id"):
      continue  
    owner= owner_of(col, tables)
  
    if not owner or owner == name:
      continue
  
    if tables[owner]["pk"] != col:
      continue

    fks.append(( col, owner))

  table["fks"] = fks


def build_create(name, table):
  lines = []

  for col in table["columns"]:
    piece = f"   {col} {table['type'][col]}"
  
    if col == table["pk"]:
      piece += " PRIMARY KEY"

    lines.append(piece)
 
  for col, owner in table["fks"]:
    lines.append(f"   FOREIGN KEY ({col}) REFERENCES {owner}({col})")

  return f"CREATE TABLE {name} (\n"+ ",\n".join(lines) + "\n)"


# 테이블 생성 순서 지정을 위한 함수
def sort_by_dependency(tables):
  done = set() 
  order = [] 

  while len(order) < len(tables):
    moved = False
  
    for name, table in tables.items():
      if name in done:
        continue
     
      if all(owner in done for _, owner in table["fks"]):
        order.append(name)
        done.add(name)
        moved = True

    if not moved:
      order += [n for n in tables if n not in done]
      break

  return order

table_order = sort_by_dependency(tables)

# 각 필드의 데이터의 타입에 맞게 변환해주는 함수
def convert(value, kind):
  if value == "":
    return None

  if kind == "INTEGER":
    return int(value)

  if kind == "FLOAT":
    return float(value)

  return value

# 앞에서 정산 테이블 생성 순서대로 데이터 저장
for name in table_order:
  table = tables[name]
  con.execute(build_create(name, table))
      
  columns = table["columns"]

  placeholders = ", ".join("?" for _ in columns)

  values = [
    tuple(convert(row[col], table["type"][col]) for col in columns) 
    for row in table["rows"] 
  ]

  con.executemany(f"INSERT INTO {name} ({", ".join(columns)}) VALUES ({placeholders})", values,)

  for col, _owner in table["fks"]:   
    con.execute(f"CREATE INDEX idx_{name}_{col} on {name}({col})")
con.commit()