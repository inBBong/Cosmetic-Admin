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

# python -m pip install langchain-text-splitters==1.1.2 transformers==5.14.1
# python -m pip install langchain-huggingface==1.2.2

# langchain-text-splitters : 글을 자르는 도구
# transformers : 토큰을 세는 도구
# langchain-huggingface : senetnce-transformers, torch(PyTorch)같이 딸려옴

# torch (PyTorch)는 벡터라이징에 필요한 행렬 계산을 해주는 엔진 : 해당 엔진위에서 임베딩, LLM모델이 구동
# sentence-transformer : transformer 기반으로 더 간단하게 청킹등의 작업을 처리해주는 편의기능

# langchain의 개념
# AI 서비스 개발을 하기 위한, 청킹, 임베딩, LLM 요청, 응답, 검증등의 일괄적인 전체 프로세스를 표준화 하기 위한 도구
# 만약 langchain이 없으면 로컬에서 허깅페이스버전으로 만들었을때 다른 상용 API 버전으로 변경시 모든 코드구조를 일일히 변경해야함
# 이떄 langchain을 쓰면 어떤 상용 API, 모델을 쓰더라도 표준 메서드명으로 통일해서 동작되는 표준규격 어댑터 제공