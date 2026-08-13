
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

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

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