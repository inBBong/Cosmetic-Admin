# 이번에 진행할 작업 - 공통으로 쓸 경로 변수에 등록

# 문자열인 경로값을 객체로 다룰수 있게 해주는 모듈
from pathlib import Path

# Path객체 내장 메서드로 현재 파일이 위치한 경로를 가져와서 다시 resolve로 절대경로로 펴고 두번 상위로 올라와서 루트 경로를 변수에 담음
ROOT = Path(__file__).resolve().parent.parent

# 루트 경로에서 하위 data폴더 경로를 이어 붙여 csv 파일이 있는 절대 경로값 변수에 저장
DATA_DIR = ROOT / "data"

# 테이블이 저장될 DB파일명과 위치를 변수에 등록
# cosmetic.db란 이름으로 db파일을 루트 경로안쪽에 생성하고 문자열로 변환해서 변수에 등록
DB_PATH = str(ROOT / "cosmetic.db")