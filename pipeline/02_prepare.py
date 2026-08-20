import sqlite3
import statistics
import sys
import tqdm
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))

# 터미널이 출력하지 못하는 이모지나 특수문자같은걸 만났을때 대체문자로 변경처리해서 에러를 방지
sys.stdout.reconfigure(errors="replace")

# transformers 실행시 발생하는 경고메시지등을 관리하는 로깅처리 모듈
from transformers import logging as hf_logging

# 청킹하는 문자가 최대 토큰개수 넘어설때 지저분하게 발생하는 에러 권고사항을 꺼줌
# 중요한 에러 문구는 그대로출력 처리
hf_logging.set_verbosity_error()

from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from transformers import AutoTokenizer
from app.config import DB_PATH, EMBED_TOKENIZER, EMBED_MAX_TOKENS

from app.retrieve import dashboard
from app.db import query

con = sqlite3.connect(DB_PATH)
con.execute("PRAGMA foreign_keys = ON")

tok = AutoTokenizer.from_pretrained(EMBED_TOKENIZER)
# 텍스트를 인자로 전달받아서 모델이 이해하는 토큰으로 나누고 토큰의 개수를 반환하는 함수
def ntok(text):    
    return len(tok.encode(text))

# 여러개의 문장을 토큰화 했을 때 최소, 중간, 최대 토큰개수를 파악하는 함수
def dist(values):
    return (f"최소 {min(values)} / 중앙 {int(statistics.median(values))} / 최대 {max(values)}")

# 접두어를 포함시켜 본문 생성 함수 (모델에게 전달하는 데이터의 문맥을 빠르게 파악시키기 위함)
# 세번쨰로 전달되는 인자값은 2차 청킹된 데이터가 1차 청킹만 완료된 본문
def with_context(pname, section, body):
    return f"[{pname} > {section}]{body}"

# [스킨로션 > 주의사항] 어쩌구 이렇게 써야 됩니다.




CHUNK_SIZE =384
CHUNK_SIZEFORTEST = 100
CHUNK_OVERLAP = 48
PREFIX_BUDGET =32 #접두사 [제품명 > 중제목] 본문내용
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
    # 각 상품별 청킹하기 전 상태의 제품상세 설명 데이터의 토큰 수 모음
    full_tokens = [ntok(detail) for _,_, detail in details]
    # 원본에서 각 청크데이터 중 최대토큰수를 초과하는 조각
    over = [n for n in full_tokens if n > EMBED_MAX_TOKENS ]

    # 글에서 ## 제품소개, ## 주요성분 같은 2단계 제목을 발견할 때 마다 본문을 분리해서 저장할 빈 리스트 생성
    sections = []

    for pid, pname, detail in tqdm.tqdm(details, desc="1차 청킹(마크다운)", unit=" 글"):
        for doc in md_splitter.split_text(detail):
            text = doc.page_content.strip() # 앞뒤공백이 제거된 md제목기준으로 나눈 본문 덩어리

            if not text:
                continue

            sections.append((pid,pname,doc.metadata.get("section", ("머릿말")),text))
            # (제품아이디, 제품이름, 마크다운 제목, 제목에 해당하는 본문내용)

    # 2단계 - 1단계에서 분리한 본문내용의 최대 토큰수용치를 넘어설때 2차 청킹 필요
    resplitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        tok, chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, separators=SEPERATORS,keep_separator="end"
    )

    rows = [] #(product_id, product_name, section, chunk_index, body)
    n_resplit = 0

    for pid, pname, section, text in tqdm.tqdm(sections, desc="2차 청킹(토큰)", unit=" 섹션"):
        # md파일에서 잘라낸 본문내용이 최대토큰수보다 넘어서면 카운트 1 증가시키면서 2차 청킹작업 시작
        if ntok(text) >RESPLIT_OVER:
            n_resplit +=1
            parts = resplitter.split_text(text)
        else:
            parts= [text]

        for i,part in enumerate(parts):
            rows.append((pid,pname,section, i, part))

    example = next(r for r in rows if r[2] =="주의사항")
    print(f" 붙이기 전 :{example[4][:30]}")
    print(f" 붙인 후 :  {with_context(example[1],example[2],example[4][:30])}...")
    section_tokens = [ ntok(t) for _,_,_,t in sections ] # 개별 섹션 별 토큰 수
    chunk_tokens = [ntok(body) for *_, body in rows] # 청킹된 본문텍스트의 토큰 수
    #print(section_tokens)
    #print(chunk_tokens)

    print(f" 0단 (통짜일때) {len(full_tokens)} {dist(full_tokens)}")
    print(f" 0단에서 상한({EMBED_MAX_TOKENS}) 초과가 {len(over)}건")
    print(f" 1단 (md 형식으로 잘랐을 때) {len(sections)} {dist(section_tokens)}")
    print(f" 2단 (문장단위로 잘랐을 때) {len(rows)} {dist(chunk_tokens)}")
    print(f" {sum(n > EMBED_MAX_TOKENS for n in chunk_tokens)}개 / {len(sections)}개")
    print(tok.encode("안녕하세요"))
    print(tok.decode([0, 107687, 2]))

    # 목적에 맞는 청킹 처리 (우리가 청킹을 하는 이유)
    # 데이터 청킹을 짧게 해야할 때 vs 길게 해야할 때
    # - 청킹데이터를 짜르는 이유는 : 사용자가 질문한 맥락에 맞는 자료조각을 탐색하기 위함
    # - 탐색이 완료되면 제일 연관도가 높은 조각들을 비교해서 그 조각이 바라보는 원문을 사용자에게
    # 내보내면 됨
    # - 선택된 위의 원문과 사용자 정보를 조합해서 LLM 전달
    # - LLM 제공받은 정보를 통해서 그럴싸한 문장을 만들어내 내보내줌





    """
    문자 데이터 청킹 흐름 (보통 실무에서 아래 순서로 작업 프로세스가 고착화되어 있음)

    **필수로 이해해야 되는 개념**
    1- 일단 마크다운의 제목 구분자로 해서 의미단위로 먼저 짜름 (의미단의)
    (분기-A) 1차 단계에서 모든 청킹데이터가 최대토큰수안에 들어오면 그냥 무시
    (분기-B) 1차 단계에서 따른 청킹데이터중 최대토큰을 넘어가는게 있으면 2차 청킹작업 시작

    2- 1차에서 짤린 청킹덩어리중 최대토큰이 넘어가는 덩어리는 다시 반복돌면서 이번엔 문장단위로 청킹시도 (문장단위)

    **추가적으로 알아두면 좋은 개념**
    [상품명 > 위치] 본문내용 : 이런식으로 본문앞에 구분자를 붙이는 이유 
    - LLM 한테 청킹된 데이터를 전달할때 해당 데이터의 제목과 출처를 같이 알려줘서 본문 데이터의 맥락을 파악하게 하기 위함 
  """