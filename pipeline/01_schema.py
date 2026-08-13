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
    print(f"\n{path.name} ({len(rows)} 행, {len(columns)} 열):")
