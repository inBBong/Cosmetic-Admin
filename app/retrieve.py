"""
db.py : DB의 데이터를 조회하는 DB제어의 코어 로직이 담겨있음 (resposity 계층)
retrieve.py : 해당 DB조회함수를 가져와서 고객이 사용할 수 있는 서비스 로직을 담는 계층 (service 계층)

앞으로 이곳에 추가할 서비스 로직들
- 벡터검색 : 질문을 주면 관련 있는 문서 조각을 찾아옴
- 마스킹 : 후기정보에서 개인정보를 가려서 내보내는 것
- 추천후보 : 특정고객에게 팔릴만 한 상품 추리는 것
"""

# 12시 20분까지
# customers 테이블에서 고객아이디가 "C001"인 고객의 모든 정보를 가지고 오되 purchases 테이블에서 해당 고객이
# 구매한 상품의 총 갯수도 같이 가져오는 로직을 dicts함수를 이용해서 반환

from app.db import dicts
# 고객목록 + 각 고객의 구매 건수 반환 함수
def customer_list(limit=None):
    sql ="""
    SELECT customers.name, customers.customer_id, COUNT(purchases.purchase_id) AS "구매 건수"
    FROM customers LEFT JOIN purchases
    ON purchases.customer_id = customers.customer_id AND purchases.is_holdout =0
    GROUP BY customers.name, customers.customer_id
    ORDER BY "구매 건수" DESC
    """
    vip = dicts(sql)
    return vip[:limit] if limit else vip

if __name__=='__main__':
    print(customer_list(5))
    