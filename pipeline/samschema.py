# 정규표현식 검사해주는 파이썬 전용 패키지 
import re
import csv
from pathlib import Path
import sqlite3

# 폴더 구조가 중첩되어 있기 때문에 루트 경로를 변수에 저장
ROOT = Path(__file__).resolve().parent.parent
# 루트경로에서 data폴더가 있는 경로를 다시 변수에 저장
DATA_DIR = ROOT / "data"

# 디비파일 생성위치 지정
db_file = ROOT / "cosmetic.db"

if db_file.exists():
  db_file.unlink()

# 해당 구문이 실행되는 순간 자동적으로 db파일이 없으면 자동 생성되며 연결
con = sqlite3.connect(db_file)

# 외래키 검사 설정
# PRAGMA는 sqlite 자체 설정을 변경하는 구문, 연결때마다 활성화 시켜야함
con.execute("PRAGMA foreign_keys = ON")

# 인자로 csv파일이 있는 패스 경로를 전달하면 각 파일의 필드명만 리스트형태로 반환하는 함수
def read_csv(path):
  with open(path, encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    return reader.fieldnames, list(reader)

# csv파일을 반복돌면서 read_csv함수 호출해서 각 파일당 필드데이터와 각 row 데이터정보를 출력
for path in sorted(DATA_DIR.glob("*.csv")):
  columns, rows = read_csv(path)

  # 각 csv파일의 첫번째의 모든 필드값 확인
  for column in columns:
    value = rows[0][column]


# 해당 값이 정수인지 확인하는 함수
def looks_int(text):
  # 만약 음수 부호 "-"이 있으면 떼서 저장
  body = text[1:] if text.startswith("-") else text

  # 0~9가 아닌 글자가 섞여있으면
  if not body.isdigit():
    # 정수가 아님   
    return False
  # 만약에 정수일때 앞자리가 0으로 시작하면 전화번호 (조건 2자리이상일떄)
  return not (len(body) > 1 and body.startswith("0"))


# 소수 판별 함수
def looks_float(text): 

  # float 실수반환되는지 우선 확인
  try:
    float(text)

  # 위의 모든 경우가 아니면 실수가 아닌게 확실하니 False반환
  except ValueError:
    return False

  # 점이 없으면 실수가 아닌것이니 최종 확인용
  if "." not in text:
      return False

  # 위의 모든 예외사항 통과하면 얘는 무조건 실수
  return True


# 날짜 판별 함수
def looks_date(text):
  # \d (숫자)
  # \d{갯수} (숫자가 저 갯수만큼 일때)
  # fullmatch(검증할 정규표현식, 검사할 문자값)
  return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None

# 타입 추론 함수 생성
def infer_type(values):
  #전달된 값에서 빈칸을 제외한 값을 변수에 담음
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

    # next(조건에 맞는 값, 디폴트값) -> 조건에 맞는 값이 반복되면 하나만 출력하고 건너뜀, 조건문으로 빈 문자열 출력 그렇게 건너뛴 값을 반환
    # 반복되는 필드명을 한번만 출력하고 싶을때
    # example = next((r[column] for r in rows if r[column] != ""), "")

    # print(f" {column} : {kind}")


# PK를 찾아주는 함수
def infer_pk(columns, rows):
  # _id로 끝나지 않는 필드명은 제외
  for col in columns:
    if not col.endswith("_id"):
      continue

    # value값이 빈문자열은 제외
    values = [r[col] for r in rows]
    if "" in values: 
      continue

    # value값이 중복되지 않으면 그건 PK
    if len(set(values)) == len(values):
      return col

  # 위의 조건이 모두 만족하지 않는다면 PK가 없음
  return None

# 특정 PK의 주인 테이블 찾기
def owner_of(column, tables):
  # 첫번쨰 인자로 들어온 PK에서 _id제거하고 그 뒤에 s, es붙여서 
  # 두번째 인자로 들어온 테이블이름 리스트랑 매칭이 되는 이름을 찾음 (해당PK의 주인 테이블 명)
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
for name, table in tables.items(): # 표 이름과 내용을 그룹으로 꺼냄
  # 특정테이블에 복수개의 외래키가 담길수 있으므로 빈 리스트 생성
  fks = []

  # 현재 반복도는 테이블의 컬럼명 끝에 _id없으면 (PK, FK 아님)
  for col in table["columns"]:
    if not col.endswith("_id"):
      continue

    # 테이블의 PK의 주인 테이블몇 찾음
    owner= owner_of(col, tables)

    # 현재반복도는 후보 키값들 중에서 owner값이 동일하면 FK제외 (PK)
    if not owner or owner == name:
      continue

    #반복도는 테이블의 주인키와 현재 컬림의 키값이 같지 않으면
    if tables[owner]["pk"] != col:
      continue

    #fks란 빈 배열에 FK,테이블 명 저장
    fks.append(( col, owner))

  table["fks"] = fks


# 지금까지 생성한 정보로 테이블 생성하는 sql구문 생성 함수
# CREATE TABLE purchases (
#   purchase_id TEXT PRIMARY KEY,
#   cutomer_id TEXT,
#   quantity INTIGER,
#   FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
# )

def build_create(name, table):
  lines = []

  # 테이블 생성 sql 괄호 안의 구문을 컴럼 정보로 반복 돌며 lines에 리스트로 담음
  for col in table["columns"]:
    piece = f"   {col} {table['type'][col]}"

    # 이때 만약 반복도는 해당 컬럼이 PK로 지정되어 있으면 오른쪽에 "PRIMARY KEY"문구 추가
    if col == table["pk"]:
      piece += " PRIMARY KEY"

    lines.append(piece)

  #table정보에서 fks 값을 반복돌며 외래키, 참조테이블명 추출 (col:외래키, owner:참조테이블명)
  # 추출된 정보로 마지막 외래키 지정 sql문 추가로 이어붙임
  for col, owner in table["fks"]:
    lines.append(f"   FOREIGN KEY ({col}) REFERENCES {owner}({col})")

  # 마지막으로 제일 상단 테이블 상단 구문과 ()안 반복 구문을 이어붙임
  return f"CREATE TABLE {name} (\n"+ ",\n".join(lines) + "\n)"


# #현재 모든 테이블명과 테이블정보를 가져와서 반복처리
# for name, table in tables.items():
#   # 반복도는 name(테이블명), table(테이블정보)를 이용해 build_create()함수 반복 호출
#   # 결국 CSV파일의 갯수에 따라 테이블 생성 SQL문 자동 생성
#   print(build_create(name, table)+";\n")


# 테이블 생성 순서 지정을 위한 함수
def sort_by_dependency(tables):
  done = set() # scan이 아닌 search로 리스트에 특정 정보의 존재유무를 빠르게 파악하기 위함
  order = [] # 실제 어떤 정보값들을 차례대로 담기 위함

  # 테이블생성 sql문이 실행될 순서의 리스트가 다 담길때까지 무한 반복
  while len(order) < len(tables):
    moved = False

    #각 csv파일 정보를 반복
    for name, table in tables.items():
      if name in done:
        continue

      # 현재 반복도는 csv파일 정보에 참조하는 내용이 없으면 
      # 참조당하는 테이블이니 우선적으로 order와 done에 담아주고 
      # 이 다음 코드가 무시되면서 다음번 루프로 돌아감
      if all(owner in done for _, owner in table["fks"]):
        order.append(name)
        done.add(name)
        moved = True

    # 참조당하는 테이블이 모두 order에 담기면 moved값이 False로 바뀌며 
    # 아래구문이 실행되며 나머지 참조하는 테이블 순서가 모두 이후에 담기게 됨
    if not moved:
      order += [n for n in tables if n not in done]
      break

  return order

table_order = sort_by_dependency(tables)

#각 필드의 데이터의 타입에 맞게 변환해주는 함수
def convert(value, kind):
  if value =="":
    return None
  if kind =="INTEGER":
    return int(value)

  if kind =="FLOAT":
    return float(value)

  return value

# 앞에서 정한 테이블 생성 순서대로 데이터 저장
for name in table_order:
    table =tables[name]
    con.execute(build_create(name, table))
 
    columns = table["columns"]

    # 컬럼이 8개면 "?,?,?,?,?"
    # 컬럼의 갯수만큼 ?로 만들어서 ", "로 이어진 문구를 insert문 뒤에 이어붙임
    placeholders= ", ".join("?" for _ in columns)

    # 모든 행을 각각의 (값, 값, 값)
    values =[
      # 테이블의 컬럼명을 다 뽑아서 convert함수의 각각 value값과 변환되어야 하는 타입을 지정
      # 튜플(타입으로 변환된 value1, value2)
      tuple(convert(row[col], table["type"]) for col in columns) # 한 행을 타입에 맞게 바꿔 튜플로 저장
      for row in table["rows"] # 이걸 모든 행에 대해서 반복처리
    ]

  # INSERT INTO 테이블명 (컬럼,컬럼,컬럼,컬럼) values (값,값,값,값)
  # INSERT INTO 테이블명 (컬럼,컬럼,컬럼,컬럼) values (?,?,?,?),(값,값,값,값)
    con.executemany(f"INSERT INTO {name} ({",".join(columns)}) VALUES ({placeholders})" , values,)

con.commit()

