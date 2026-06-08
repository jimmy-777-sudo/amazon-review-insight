import requests
import time
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class SellerspriteClient:
    """
    卖家精灵 API 封装
    文档参考：https://open.sellersprite.com/
    """
    
    BASE_URL = "https://open.sellersprite.com/api/v1"
    RATE_LIMIT = 40  # 每分钟 40 次
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._last_request_time = 0
        self._min_interval = 60.0 / self.RATE_LIMIT  # 每次请求最小间隔（秒）
    
    def _rate_limit(self):
        """遵守 API 频率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(self, endpoint: str, params: dict = None) -> dict:
        """通用请求方法"""
        self._rate_limit()
        url = f"{self.BASE_URL}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            raise
    
    def get_reviews(self, asin: str, site: str = "amazon.com", max_reviews: int = 100) -> List[str]:
        """
        获取 ASIN 的评论列表（1-3 星）
        
        注意：卖家精灵 API 可能不直接提供评论内容，此方法会尝试多个端点。
        如果无法获取，返回空列表，由上层逻辑提示用户手动粘贴。
        """
        reviews = []
        
        # 尝试获取评论（根据卖家精灵实际 API 调整）
        # 这里使用通用参数，实际端点需参考官方文档
        params = {
            "asin": asin,
            "site": site,
            "star_rating": "1,2,3",  # 1-3 星
            "page_size": min(max_reviews, 100),
            "page": 1
        }
        
        try:
            # 尝试评论列表接口（需根据实际 API 文档调整）
            data = self._request("review/list", params)
            if data and "data" in data and "reviews" in data["data"]:
                for review in data["data"]["reviews"]:
                    if "content" in review:
                        reviews.append(review["content"])
                    elif "text" in review:
                        reviews.append(review["text"])
                
                # 分页处理
                total_pages = data["data"].get("total_pages", 1)
                for page in range(2, total_pages + 1):
                    if len(reviews) >= max_reviews:
                        break
                    params["page"] = page
                    page_data = self._request("review/list", params)
                    if page_data and "data" in page_data and "reviews" in page_data["data"]:
                        for review in page_data["data"]["reviews"]:
                            if len(reviews) >= max_reviews:
                                break
                            if "content" in review:
                                reviews.append(review["content"])
                            elif "text" in review:
                                reviews.append(review["text"])
        except Exception as e:
            logger.warning(f"获取评论失败（可能 API 不支持直接获取评论）: {e}")
            # 不抛出异常，返回空列表让上层处理
        
        return reviews[:max_reviews]
    
    def get_product_info(self, asin: str, site: str = "amazon.com") -> Optional[dict]:
        """获取产品基本信息（备用）"""
        params = {
            "asin": asin,
            "site": site
        }
        try:
            data = self._request("product/detail", params)
            if data and "data" in data:
                return data["data"]
        except Exception as e:
            logger.warning(f"获取产品信息失败: {e}")
        return None
    
    def get_keyword_data(self, asin: str, site: str = "amazon.com") -> Optional[dict]:
        """获取关键词数据（备用）"""
        params = {
            "asin": asin,
            "site": site
        }
        try:
            data = self._request("keyword/asin", params)
            if data and "data" in data:
                return data["data"]
        except Exception as e:
            logger.warning(f"获取关键词数据失败: {e}")
        return None
