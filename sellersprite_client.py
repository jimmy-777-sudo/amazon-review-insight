import requests
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class SellerspriteClient:
    """
    卖家精灵 REST API 封装
    API 文档参考: https://api.sellersprite.com
    """
    
    BASE_URL = "https://api.sellersprite.com/v1"
    RATE_LIMIT = 40  # 40 requests per minute
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
        self._last_request_time = 0
    
    def _rate_limit(self):
        """Simple rate limiting to avoid hitting API limits"""
        elapsed = time.time() - self._last_request_time
        min_interval = 60.0 / self.RATE_LIMIT
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(self, endpoint: str, params: dict = None, method: str = "GET") -> dict:
        """
        Make an API request with rate limiting
        """
        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url, params=params, timeout=30)
            elif method == "POST":
                response = self.session.post(url, json=params, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
    
    def get_reviews(self, asin: str, site: str = "amazon.com", max_reviews: int = 100) -> List[str]:
        """
        获取 ASIN 的评论数据
        
        由于卖家精灵 API 可能不直接提供评论内容，此方法会尝试多个端点获取数据。
        如果无法获取评论，返回空列表。
        """
        reviews = []
        
        # Try to get reviews from product review API
        try:
            # Attempt to fetch reviews using available endpoints
            # Note: Actual endpoint may vary based on API version
            params = {
                "asin": asin,
                "site": site,
                "page": 1,
                "page_size": min(max_reviews, 100),
                "star_rating": "1,2,3"  # Focus on 1-3 star reviews
            }
            
            # Try review endpoint (if available)
            try:
                data = self._request("product/reviews", params=params)
                if data and "reviews" in data:
                    for review in data["reviews"]:
                        if "content" in review:
                            reviews.append(review["content"])
                        elif "text" in review:
                            reviews.append(review["text"])
            except Exception as e:
                logger.warning(f"Review endpoint failed: {e}")
            
            # If no reviews, try to get product info and keywords
            if not reviews:
                logger.info("No reviews from API, trying product info...")
                product_info = self.get_product_info(asin, site)
                if product_info:
                    # If we have product info, we can still provide some analysis
                    # Return empty list to indicate manual input needed
                    pass
        except Exception as e:
            logger.error(f"Failed to fetch reviews: {e}")
        
        return reviews
    
    def get_product_info(self, asin: str, site: str = "amazon.com") -> Optional[dict]:
        """
        获取产品基础信息
        """
        try:
            params = {
                "asin": asin,
                "site": site
            }
            data = self._request("product/info", params=params)
            return data
        except Exception as e:
            logger.error(f"Failed to fetch product info: {e}")
            return None
    
    def get_keywords(self, asin: str, site: str = "amazon.com") -> List[str]:
        """
        获取产品关键词数据
        """
        try:
            params = {
                "asin": asin,
                "site": site
            }
            data = self._request("product/keywords", params=params)
            if data and "keywords" in data:
                return [kw["keyword"] for kw in data["keywords"]]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch keywords: {e}")
            return []
