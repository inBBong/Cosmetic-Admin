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
#mission : 고객아이디를 인수로 전달해서 해당 고객에 대한 정보와 구매내역을 가져오는 함수를 만들자
def purchaseInfo(cid):
    sql="""
    SELECT *
    FROM purchases    
    WHERE customer_id = ?
    """
    return dicts(sql,(cid,))
# 특정 고객 아이디를 집어넣으면 다음의 정보를 반환하는 함수
# {customers: {고객정보}, avg_rating: 평균평점, total_spent: 구매한 상품의 총 금액,
#  by_category: 구매한 상품명 + 상품갯수, purchases : 구매횟수 + 리뷰}
def dashboard(customer_id):    
    # 기본 고객정보를 별도의 딕셔너리 형태로 변환받음
    profile = dicts("""
        SELECT customer_id, name, age, gender, skin_type, city -- 보안이 중요한 고객정보인 전화번호, 이메일은 애초에 제외하고 데이터 호출
        FROM customers WHERE customer_id = ?
    """,(customer_id,))
    #위에서 반환받은 고객 정보가 없으면 이후의 탐색문이 무의미하므로 강제 함수 종료
    if not profile:
        return None

    #상품이름, 카테고리, 가격은 products 표에 있고,
    #구매일, 별점, 후기는 purchases 표에 있으므로 조인해서 한번에 꺼냄
    products=dicts("""
        SELECT products.product_id, products.name, products.category,products.price,purchases.purchased_at, purchases.rating,purchases.review
        FROM purchases JOIN products ON purchases.product_id=products.product_id -- 구매목록의 상품아이디와 상품목록의 상품아이디가 같은 정보를 조인해서 가져옴        
        WHERE purchases.customer_id=?
    """,(customer_id,))

    return {
        "customers" : profile,
        "products" : products
    }


    
if __name__=='__main__':
    #print(customer_list(5))
    #print(purchaseInfo("C001"))
    print(dashboard("C002"))