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

from langchain_text_splitters import MarkdownHeaderTextSplitter

from transformers import AutoTokenizer
from app.config import DB_PATH, EMBED_TOKENIZER, EMBED_MAX_TOKENS

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")

tok = AutoTokenizer.from_pretrained(EMBED_TOKENIZER)
# 텍스트를 인자로 전달받아서 모델이 이해하는 토큰으로 나누고 토큰의 개수를 반환하는 함수
def ntok(text):    
    return len(tok.encode(text))

# 여러개의 문장을 토큰화 했을 때 최소, 중간, 최대 토큰개수를 파악하는 함수
def dist(values):
    return (f"최소 {min(values)} / 중앙 {int(statistics.median(values))} / 최대 {max(values)}")

from app.retrieve import dashboard
from app.db import query

CHUNK_SIZE =384
CHUNK_OVERLAP = 48
PREFIX_BUDGET =32 #접두사 [상품명 > 위치] 본문내용
RESPLIT_OVER = EMBED_MAX_TOKENS-PREFIX_BUDGET
HEADERS = [("##","section")] #청킹할 데이터의 표시 경계 구분점 생성(Markdown)
SEPERATORS = ["\n\n","\n","다","요",".",",",""]

#Document(
#    page_content="수분을 공급하는 크림입니다"
#    metadata={"section" : "제품소개"}
#)

# 지금부터는 글자수가 아니라 '## 주의사항' 같은 md의 제목을 경계로 해서 문자를 자름(청킹)
md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)



if __name__ == "__main__":
    details = query("""
        SELECT product_details.product_id, products.name, product_details.detail
        FROM product_details JOIN products ON product_details.product_id =products.product_id
        ORDER BY product_details.product_id
    """)

    # 글에서 ## 제품소개, ## 주요성분 같은 2단계 제목을 발견할 때 마다 본문을 분리해서 저장할 빈 리스트 생성
    sections = []

    for pid, pname, detail in details:
        for doc in md_splitter.split_text(detail):
            text = doc.page_content.strip() # 앞뒤공백이 제거된 md제목기준으로 나눈 본문 덩어리

            if not text:
                continue

            sections.append((pid,pname,doc.metadata.get("section", ("머릿말")),text))
            # (제품아이디, 제품이름, 마크다운 제목, 제목에 해당하는 본문내용)

    print(sections[0])