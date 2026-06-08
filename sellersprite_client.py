"""
卖家精灵 MCP 客户端 — JSON-RPC over HTTP
端点: https://mcp.sellersprite.com/mcp
传输: streamableHttp (基于实际 API 测试验证)
"""
import json
import time
import logging
import urllib.request
import urllib.error
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SellerspriteClient:
    """卖家精灵 MCP JSON-RPC 客户端"""

    MCP_URL = "https://mcp.sellersprite.com/mcp"
    RATE_LIMIT = 40  # 每分钟 40 次

    HEADERS_TEMPLATE = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._request_id = 0
        self._last_request_time = 0.0
        self._min_interval = 60.0 / self.RATE_LIMIT
        self._tools: Dict[str, dict] = {}
        self._initialized = False

    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _rpc_call(self, method: str, params: dict = None) -> dict:
        """发送 JSON-RPC 请求"""
        self._rate_limit()

        headers = {**self.HEADERS_TEMPLATE, "secret-key": self.api_key}

        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }).encode("utf-8")

        req = urllib.request.Request(
            self.MCP_URL, data=payload, headers=headers, method="POST"
        )
        self._last_request_time = time.time()

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"MCP 请求失败 [{e.code}]: {err_body}") from e

        if "error" in body:
            err = body["error"]
            raise ConnectionError(f"MCP 错误 [{err.get('code')}]: {err.get('message')}")

        return body.get("result", body)

    def initialize(self) -> dict:
        """MCP 握手"""
        result = self._rpc_call("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {
                "name": "amazon-review-insight",
                "version": "1.0.0"
            }
        })
        self._initialized = True
        return result

    def discover_tools(self) -> List[dict]:
        """发现可用工具列表"""
        if not self._initialized:
            self.initialize()
        result = self._rpc_call("tools/list", {})
        tools = result.get("tools", [])
        for tool in tools:
            self._tools[tool["name"]] = tool
        return tools

    def call_tool(self, name: str, arguments: dict) -> Any:
        """调用 MCP 工具"""
        result = self._rpc_call("tools/call", {
            "name": name,
            "arguments": arguments
        })
        content = result.get("content", [])
        texts = []
        for item in content:
            if item.get("type") == "text":
                text = item["text"]
                # 尝试解析为 JSON
                try:
                    parsed = json.loads(text)
                    texts.append(parsed)
                except (json.JSONDecodeError, TypeError):
                    texts.append(text)
            elif item.get("type") == "resource":
                texts.append(item.get("resource", {}))
        return texts[0] if len(texts) == 1 else texts

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys()) if self._tools else []

    # ---- 业务方法 ----

    def get_product_info(self, asin: str, marketplace: str = "US") -> Optional[dict]:
        """获取产品详情（asin_detail 工具）"""
        result = self.call_tool("asin_detail", {
            "marketplace": marketplace,
            "asin": asin
        })
        if isinstance(result, dict):
            data = result.get("data", result)
            return data
        return None

    def get_reviews(self, asin: str, marketplace: str = "US",
                    max_reviews: int = 100, star_ratings: List[str] = None) -> List[dict]:
        """
        获取评论列表（review 工具）

        返回评论列表，每条包含: star, title, content, reviewer, date 等
        """
        if star_ratings is None:
            star_ratings = ["1", "2", "3"]

        all_items = []
        page = 1
        size = min(max_reviews, 50)

        while True:
            result = self.call_tool("review", {
                "marketplace": marketplace,
                "asin": asin,
                "starList": star_ratings,
                "page": page,
                "size": size
            })

            data = result.get("data", result) if isinstance(result, dict) else {}
            items = data.get("items", [])
            total = data.get("total", 0)
            pages = data.get("pages", 0)

            if not items:
                break

            all_items.extend(items)

            if (len(all_items) >= max_reviews or
                    len(all_items) >= total or
                    page >= pages):
                break

            page += 1

        return all_items[:max_reviews]

    def get_review_texts(self, asin: str, marketplace: str = "US",
                         max_reviews: int = 100) -> List[str]:
        """获取评论纯文本列表（方便 AI 分析）"""
        items = self.get_reviews(asin, marketplace, max_reviews)
        texts = []
        for item in items:
            content = item.get("content") or item.get("title") or ""
            title = item.get("title") or ""
            star = item.get("star", "")
            if title and title != content:
                parts = [f"[{star}星] {title}", content]
            else:
                parts = [f"[{star}星] {content}"]
            texts.append(" | ".join(p for p in parts if p))
        return texts

    def get_keyword_data(self, asin: str, marketplace: str = "US") -> Optional[dict]:
        """获取流量关键词数据"""
        result = self.call_tool("traffic_keyword_stat", {
            "marketplace": marketplace,
            "asin": asin
        })
        if isinstance(result, dict):
            return result.get("data", result)
        return None

    def get_sales_trend(self, asin: str, marketplace: str = "US") -> Optional[dict]:
        """获取销量趋势"""
        result = self.call_tool("asin_sales_trend", {
            "marketplace": marketplace,
            "asin": asin
        })
        if isinstance(result, dict):
            return result.get("data", result)
        return None

    def get_keepa_info(self, asin: str, marketplace: str = "US") -> Optional[dict]:
        """获取 Keepa 商品趋势数据"""
        result = self.call_tool("keepa_info", {
            "marketplace": marketplace,
            "asin": asin
        })
        if isinstance(result, dict):
            return result.get("data", result)
        return None
