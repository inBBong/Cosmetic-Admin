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

    #=====================================================
    # 청킹 데이터가 들어갈 테이블 생성
    #=====================================================





    # 목적에 맞는 청킹 처리 (우리가 청킹을 하는 이유)
    # 데이터 청킹을 짧게 해야할 때 vs 길게 해야할 때
    # - 청킹데이터를 짜르는 이유는 : 사용자가 질문한 맥락에 맞는 자료조각을 탐색하기 위함
    # - 탐색이 완료되면 제일 연관도가 높은 조각들을 비교해서 그 조각이 바라보는 원문을 사용자에게
    # 내보내면 됨
    # - 선택된 위의 원문과 사용자 정보를 조합해서 LLM 전달
    # - LLM 제공받은 정보를 통해서 그럴싸한 문장을 만들어내 내보내줌
    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys = ON")

    # 테이블이 만들어지는 순서는 section -> chunks -> chunk_vectors순이기 때문에
    # 테이블 제거시에는 역순으로 제거
    con.execute("DROP TABLE IF EXISTS chunk_vectors")   # 의미 추론을 위한 조각들의 좌표값이 들어가는 테이블
    con.execute("DROP TABLE IF EXISTS chunks")          # 사용자 요청시 빠르게 문맥에 맞는 키워드를 탐색하기 위한 조각들 ( 해당 조각이 원문인 섹션을 바라봄)
    con.execute("DROP TABLE IF EXISTS sections")        # LLM이 참고해야 되는 원문이 들어가는 테이블

    con.execute("""
      CREATE TABLE sections (
        section_id   INTEGER PRIMARY KEY,  --자동으로 들어가는 값 레코드가 추가될때마다 1씩 자동카운트
        product_id   TEXT NOT NULL,        --어느 상품인지
        section      TEXT NOT NULL,        --'주의사항' 같은 항 섹션별 제목
        text         TEXT NOT NULL,        --접두어가 붙기전의 원문
        n_tokens     INTEGER NOT NULL,     --해당 청크 데이터의 토큰수 (미리 세어서 집어넣으면 시간 절약)
        FOREIGN KEY (product_id) REFERENCES products(product_id)
      )
    """)

    con.execute("""
      CREATE TABLE chunks (
        chunk_id     INTEGER PRIMARY KEY,   -- 자동으로 들어가는 각 레코드 PK  
        section_id   INTEGER NOT NULL,      -- 해당 청킹된 조각이 바라보는 섹션 테이블 아이디
        product_id   TEXT NOT NULL,         -- 해당 청킹된 조각이 바라보는 제품 아이디
        section      TEXT NOT NULL,         -- '주의사항' 같은 항 섹션별 제목
        text         TEXT NOT NULL,         -- 접두어가 붙기전의 원문
        body         TEXT NOT NULL,         -- 접두어가 붙은 원문
        n_tokens     INTEGER NOT NULL,
        FOREIGN KEY (section_id) REFERENCES sections(section_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id),
      )
    """)

    # 생성된 테이블의 외래키 컬럼에 index 추가
    con.execute("CREATE INDEX idx_chunks_proudct_id ON chunks(product_id)")
    con.execute("CREATE INDEX idx_sections_proudct_id ON chunks(product_id)")
    
    # ===================================
    #  테이블에 데이터 저장
    # ====================================

    # sections 테이블에 데이터 저장
    section_id_of = {}
    # {
    #   ("P001","제품설명"):1,
    #   ("P001","주의사항"):2,
    #   ("P001","성분"):3,
    # }

    # sections테이블과 chunks 테이블을 조인시키지 않으면 연결시킬수 있는 접점이 없음
    # 2개 테이블에 접점일수 있는 부분은 동일하게 들어가는 컬럼명인 pid, section밖에 없음
    # 저 두개의 값을 키로 활용하는 공통의 접점을 생성
    # section 테이블에서 필드값에 숫자는 무조건 정수인 PK가 지정되어 있기 때문에 공통의 컬럼값을 매칭처리 필요 (pic, section)

    # 이렇게 번거롭게 sections 테이블과 chunks 테이블을 연결하는 이유
    # 테이블에 원본데이터를 꺼낸 이후에 청킹을 시작하면 문제가 안되지만
    # 유지보수의 편의성을 위해서 실제 db에 데이터를 저장하기 전에 청킹과 벡터라이징을 다 끝내 놓은 상태
    # 이 때 청킹이 완료된 상태이기 떄문에 저 2 테이블은 연결할 방법이 없음
    # 이때 유일한 접점이 (상품아이디와 상품의 섹션 제목) 해당 필드가 공통으로 공유하는 값이 청킹 데이터가 바라봐야될 
    # 원본 테이블의 행 

    for pid, _pname, section, text in sections:
      cur = con.execute(
        "INSERT INTO sections (product_id, section, text, n_tokens) VALUES (?,?,?,?),"
        (pid, section, text, ntok(text)),
      )
      section_id_of[(pid, section)] = cur.lastrowid

    # chunks 테이블에 데이터 저장
    for pid, pname, section, chunk_index, part in rows:
      text = with_context(pname, section, part)
      con.execute("""
        INSERT INTO chunks (section_id, product_id, section, chunk_index, text, body, n_tokens)
        VALUES (?,?,?,?,?,?,?), (section_id[(pid, section)], pid, section, chunk_index, part, text, ntok(part))
      """)

    con.commit();

    #======================================================
    # 테이블에 저장된 데이터 개수와 각 청크 별 토큰 개수 확인
    #======================================================
    stored = [n for (n,) in con.execute("SELECT n_tokens FROM chunks")]
    print(f"    sections {len(sections)}행")
    print(f"    chunks {len(sections)}행")
    print(f"    상한 {len(sections)} 초과: {sum(n> EMBED_MAX_TOKENS for n in stored)}개 \n")

    

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