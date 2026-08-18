'''
 SQLite 데이터베이스 조회 기능은 모두 이곳에 모아둘 예정

 다른 파일에서 데이터조회가 필요시 이곳에 모아놓은 함수를 import 해서 사용

 from app.db import query, one
 - pipeline/01_schema.py는 초기 DB 생성, 데이터 저장의 역할만 담당
 - app/db.py는 이미 만들어진 테이블의 데이터를 조회하는 역할만 담당
 - 나중에 SQLite를 다른 DB로 교체할때 수정 범위를 줄일 수 있음
'''
import sqlite3

from app.config import DB_PATH

con = sqlite3.connect(DB_PATH)

def query(sql, params=()):
    return con.execute(sql, params).fetchall()

def one(sql, params=()):
    return con.execute(sql,params).fetchone()

def get_column_names(table_name):
    """특정 테이블의 컬럼명만 리스트로 반환하는 함수"""
    # 주의: PRAGMA 명령어는 '?' 파라미터 바인딩이 지원되지 않아 f-string을 사용합니다.
    raw_info = query(f"PRAGMA table_info('{table_name}')")
    return [row[1] for row in raw_info]
# 컬럼명이 붙은 딕셔너리 목록으로 꺼내주는 함수
def dicts(sql,params=()):
    #con.execute로 반환된 결과값에서 fetchone, fetchall로 꺼내지 않은 객체를 Cursor라고함.
    #Cursor : description, fetchall(), fetchone()
    #Cursor객체의 description에는 각 컬럼의 정보가 담겨있음
    cur=con.execute(sql,params)

    columns=[c[0] for c in cur.description]
    print(columns)


# 해당 파일의 함수는 보통 다른 파일에서 해당 함수를 각각 import 해서 다양하게 조합할때 쓰는 용도
# 지금 해당 파일을직접 실행해서 결과값을 테스트 하기 위해 직접 호출구문을 아래처럼 넣어버리면
# 추 후 다른 파일에서해당 함수 import시 해당 구문이 같이 실행됨
# 지금 파일을 직접 테스트용도로 호출할 때에만 아래 구문이 실행되도록 제한을 걸어둬야 함

#아래 구문은 직접 python명령어로 해당 파일을 호출할때 걸리게 되는 조건문
# 다른 파일에서 해당 파일의 함수를 단지 import해서 호출시에는 아래 테스트문이 실행되지 않음.
if __name__ == "__main__":
    # --- 사용 예시 ---
    # 다른 파일에서 이 함수를 import 한 뒤 아래처럼 사용하시면 됩니다.
    products_cols = get_column_names('products')
    print(products_cols)
    # products 테이블에서 제품이름을 3개만 가져오는 sql문을 params를 이용해서 호출

    rows = query("SELECT name FROM products WHERE price >= ? LIMIT 3",("10000",))
    print(rows)

    # products 테이블에서 가격이 3만원 이상이고 그와 동시에 제품판매갯수가 3개 이상인 제품 전부 호출

    rows = query("SELECT product_id FROM purchases WHERE rating >= ? AND quantity>=?  LIMIT 3",("3","3"))
    print(rows)

    # PRAGMA 쿼리 직접 치기
    rows = query("PRAGMA table_info(products)")
    print(rows)

    #재성이 형님이 올려주신 함수
    print(get_column_names("products"))

    dicts("SELECT name FROM products WHERE price >= ? LIMIT 3",("10000",))
