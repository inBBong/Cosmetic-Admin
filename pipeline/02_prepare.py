import sqlite3
import statistics
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

# 터미널이 출력하지 못하는 이모지나 특수문자같은걸 만났을때 대체문자로 변경처리해서 에러를 방지
sys.stdout.reconfigure(errors="replace")

# transformers 실행시 발생하는 경고메시지등을 관리하는 로깅처리 모듈
from transformers import logging as hf_logging

# 청킹하는 문자가 최대 토큰개수 넘어설때 지저분하게 발생하는 에러 권고사항을 꺼줌
# 중요한 에러 문구는 그대로출력 처리
hf_logging.set_verbosity_error()

from transformers import AutoTokenizer
from app.config import DB_PATH, EMBED_TOKENIZER

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")