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
if __name__ == "__main__":
    details = query("""
        SELECT product_details.product_id, products.name, product_details.detail
        FROM product_details JOIN products ON product_details.product_id =products.product_id
        ORDER BY product_details.product_id
    """)
    #print(details)
    full_tokens = [ntok(detail) for _,_, detail in details]
    print(full_tokens)
    # mission : 현재 제품 설명중에서 최대 토큰인 512토큰을 넘어가는 글의 토큰수만 다시 리스트로 분류
    print("===========================================")
    over512 = [t for t in full_tokens if t>EMBED_MAX_TOKENS]
    print(over512)
    print(f"개수 : {len(over512)}")
    # 현재 상품정보 데이터에서 지금 ai처리할때 수용되는 데이터의 퍼센트
    print("===========================================")
    #loss =[ f"{round(512/t,2)*100}%" if t>EMBED_MAX_TOKENS else "100%" for t in full_tokens ]
    loss =[ f"{round(min(n,EMBED_MAX_TOKENS)*100/n,2)}%" for n in full_tokens]
    print(loss)

    # details = [
    #     ('P001', '상품명1', "상품 1의 엄청 긴 설명" ),
    #     ('P002', '상품명2', "상품 2의 엄청 긴 설명" ),
    #     ...
    # ]
    