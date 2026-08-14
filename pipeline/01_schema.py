
# github에 내 작업을 단계별로 올리는 방법
# 1. 깃허브에가서 내가 올리고 싶은 작업의 전용 저장소 URL복사 (private)
# 2. 내 작업폴더에 터미널 열고 다음 명령어 차례대로 실행
#  git init
#  git remote add origin 저장소url
# 3. 단계별로 기록을 남기고 싶을때마다 파일 저장 -> git add . -> git commit -m "커밋메세지" -> git push origin --all
# 정규표현식 검사해주는 파이썬 전용 패키지
import re
import csv
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

#디비파일 생성위치 지정
db_file = ROOT / "cosmetic.db"

if db_file.exists():
    db_file.unlink()

#해당 구문이 실행되는 순간 자동적으로 db파일이 없으면 자동 생성되며 연결
con =sqlite3.connect(db_file)    

# 외래키 검사 설정
# PRAGMA는 sqlite 자체 설정을 변경하는 구문, 연결때마다 활성화 시켜야함
con.execute("PRAGMA foreign_keys=ON")
# 인자로 csv 파일이 있는 패스 경로를 전달하면 각 파일의 필드명만 리스트형태로 반환하는 함수
def read_csv(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)

# csv 파일을 돌면서 read_csv 함수 호출해서 각 파일당 필드데이터와 각 row 데이터 정보를 추력    
for path in sorted(DATA_DIR.glob("*.csv")):
    columns, rows = read_csv(path)
    # 실제 각 csv 파일의 필드명 확인
    print(f"==================={path.name}====================")
    for column in columns:
        value = rows[0][column]
        print(value)

# 해당 값이 정수인지 확인하는 함수
def looks_int(text):
    # 만약 음수 부호 "-"이 있으면 떼서 저장
    body=text[1:] if text.startswith("-") else text
    # 0~9가 아닌 글자가 섞여있으면
    if not body.isdigit():
        # 정수가 아님
        return False
    # 만약에 정수일때 앞자리가 0으로 시작하면 전화번호 (조건 2자리 이상일때)
    return not (len(body) > 1 and body.startswith("0"))

def looks_float(text):
    try:
        float(text)
    except ValueError:
        return False

    if "." not in text :
        return False
    
    return True

def looks_date(text):
    # 정규표현식 
    # \d (숫자)
    # \d{갯수} (숫자가 저 갯수만큼 일때)
    # fullmatch (검증할 정규표현식, 검사할 문자값)
    return re.fullmatch(r"\d{4}-\d{2}-\d{2}", text) is not None

#타입추론 함수 생성
def infer_type(text):
    if looks_int(text):
        return "int"
    elif looks_float(text):
        return "float"
    elif looks_date(text):
        return "date"
    else:
        return "str"

def infer_type(values):
    #전달된 값에서 빈칸을 제외한 값을 변수에 담음
    seen = [v for v in values if v != ""]

    if not seen:
        return "TEXT"

    if all(looks_int(v) for v in seen):
        return "INTEGER"
    elif all(looks_float(v) for v in seen):
        return "REAL"
    elif all(looks_date(v) for v in seen):
        return "DATE"

    return "TEXT"

for path in sorted(DATA_DIR.glob("*.csv")):
    columns, rows = read_csv(path)
    print(f"\n{path.stem} ({len(rows)})")

    for column in columns:
        kind = infer_type([row[column] for row in rows])

        print(f"{column}: {kind}")

## 과제 : 우리 프로젝트 데이터 파일 가져와서 타입추론 해보기.

#PK를 찾아주는 함수
def infer_pk(columns, rows):
    # _id로 끝나지 않는 필드명은 제외
    for col in columns:
        if not col.endswith("_id"):
            continue

        # value값이 빈 문자열은 제외
        values = [r[col] for r in rows]
        if "" in values:
            continue
        # value값이 중복되지 않으면 그건 PK
        if len(set(values)) == len(values):
            return col

    # 위의 조건이 모두 만족하지 않는다면 PK가 없으
    return None

# 특정 PK의 주인 테이블 찾기
def owner_of(column,tables):
    # 첫번째 인자로 들어온 PK에서 _id 제거 하고 그 뒤에 s, es붙여서
    # 두번째 인자로 들어온 테이블이름 리스트랑 매칭이 되는 이름을 찾음 (해당PK의 주인 테이블 명)
    stem =column[:-3]
    for candidate in (stem, stem+"s", stem + "es"):
        if candidate in tables:
            return candidate
        
    return None

# 1. 모든 테이블 별 필드, 데이터타입, PK 구하기
tables = {}
for path in sorted(DATA_DIR.glob("*.csv")):
    columns, rows = read_csv(path)
    tables[path.stem] = {
        "columns":columns,
        "rows":rows,
        "type": {col: infer_type([r[col] for r in rows]) for col in columns},
        "pk": infer_pk(columns,rows)
    }

# 2. 특정 테이블에 연결되어 있는 외래키 찾기
for name, table in tables.items(): # 표 이름과 내용을 그룹으로 꺼냄
    #특정테이블에 복수개의 외래키가 담길 수 있으므로 빈 리스트 생성
    fks =[]

    #현재 반복도는 테이블의 컬럼명 끝에 _id 없으면 (PK,FK 아님)
    for col in table["columns"]:
        if not col.endswith("_id"):
            continue
        # 테이블의 PK의 주인 테이블 몇 찾음
        owner = owner_of(col, table)

        # 현재 반복도는 후보 키값들 중에서 owner값이 동일하면 FK제외 (PK)
        if not owner or owner ==name:
            continue
        if tables[owner]["pk"]!=col:
            continue
        #fks란 빈 배열에 FK, 테이블 명 저장
        fks.append((name, col,owner))

        table["fks"] = fks

        print(fks)

# 3. 테이블 상세 결과 보기
#for name, table in tables.items():
#    marks=[]
#
#    if table['pk']:
#        marks.append(f"PK={table['pk']}")
#
#    for col, owner in table["fks"]:
#        print(col)

# 4. 지금까지 생성한 정보로 테이블 생성하는 sql구문 생성 함수
# 아래는 build_create 함수가 최종적으로 만들어내야 할 SQL 모양 (예시 메모)
"""
CREATE TABLE purchases(
    purchase_id TEXT PRIMARY KEY,
    customer_id TEXT,
    quantity INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
)
"""

def build_create(name, table):
    lines = []

    for col in table["columns"]:
        piece = f"    {col}{table['type'][col]}"

        if col ==table["pk"]:
            piece += " PRIMARY KEY"

        lines.append(piece)
    for col, owner in table["fks"]:
        print(col)
        lines.append(f"    FOREIGN KEY ({col}) REFERENCES {owner}({col})")

    return f"CREATE TABLE {name}(\n"+ ",\n".join(lines) + "\n)"

# 현재 모든 테이블명과 테이블 정보를 가져와서 자동으로 모든 테이블 생성 sql문 확인
for name, table in tables.items():
    print(build_create(name, table)+";\n")

# 테이블 생성 순서 지정을 위한 함수
def sort_by_dependency(tables):
    done = set() #scan이 아니라 search로 리스트에 특정 정보의 존재유무를 빠르게 파악하기 위함
    order = []  # 실제 어떤 정보값들을 차례대로 담기 위함

    #테이블 생성 sql문이 실행될 순서의 리스트가 다 담길때까지 무한 반복
    while len(order)<len(tables):
        moved =False

        #각 csv파일 정보를 반복
        for name, table in tables.items():
            if name in done:
                continue
            # 현재 반복도는 csv파일 정보에 참조하는 내용이 없으면 
            # 참조 당하는 테이블이니 우선적으로 order와 done에 담아주고
            # 이 다음 코드가 무시되면서 다시 다음번 루트로 돌아감
            if all(owner in done for _, owner in table["fks"]):
                order.apend(name)
                done.add(name)
                moved = True
        #참조당하는 테이블이 모두 order에 담기면 moved값이 False로 바뀌며
        #아래 구문이 실행되며 나머지 참조하는 테이블 순서가 모두 이후에 담기게 됨
        if not moved:
            order +=[n for n in tables if n not in done]
            break
    return order

table_order = sort_by_dependency(tables)
