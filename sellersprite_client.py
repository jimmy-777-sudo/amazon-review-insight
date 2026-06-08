"""
卖家精灵 MCP 客户端 — JSON-RPC over HTTP
端点: https://mcp.sellersprite.com/mcp
传输: streamableHttp
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
    INIT_TIMEOUT = 30

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._request_id = 0
        self._last_request_time = 0.0
        self._min_interval = 60.0 / self.RATE_LIMIT
        self._tools: Dict[str, dict] = {}
        self._session_id: Optional[str] = None

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
        payload = json.dumps({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
            "params": params or {}
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "secret-key": self.api_key,
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        req = urllib.request.Request(
            self.MCP_URL, data=payload, headers=headers, method="POST"
        )

        self._last_request_time = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                if sid:
                    self._session_id = sid
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"MCP 请求失败 [{e.code}]: {err_body}") from e

        if "error" in body:
            err = body["error"]
            raise ConnectionError(f"MCP 错误 [{err.get('code')}]: {err.get('message')}")

        return body.get("result", body)

    def initialize(self) -> dict:
        """MCP 握手 — 获取服务端能力和 session"""
        result = self._rpc_call("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "amazon-review-insight",
                "version": "1.0.0"
            }
        })
        self._rpc_call("notifications/initialized", {})
        return result

    def discover_tools(self) -> List[dict]:
        """发现可用工具列表"""
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
                texts.append(item["text"])
            elif item.get("type") == "resource":
                texts.append(json.dumps(item.get("resource", {}), ensure_ascii=False))
        return "\n".join(texts) if texts else result

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_product_info(self, asin: str, site: str = "amazon.com") -> Optional[dict]:
        """获取产品详情（自动匹配 MCP 工具）"""
        candidates = ["get_asin_info", "product_info", "product_detail",
                       "asin_detail", "get_product", "asin_info"]

        for name in candidates:
            if name in self._tools:
                raw = self.call_tool(name, {"asin": asin, "site": site})
                return self._parse_json(raw)

        available = self.list_tool_names()
        logger.warning(f"未找到产品详情工具，可用工具: {available}")
        return {"error": "no_matching_tool", "available_tools": available}

    def get_reviews(self, asin: str, site: str = "amazon.com",
                    max_reviews: int = 100) -> List[str]:
        """获取评论列表（自动匹配 MCP 工具）"""
        candidates = ["get_reviews", "review_list", "product_reviews",
                       "asin_reviews", "get_product_reviews"]

        for name in candidates:
            if name in self._tools:
                raw = self.call_tool(name, {
                    "asin": asin,
                    "site": site,
                    "star_rating": "1,2,3",
                    "page_size": min(max_reviews, 100),
                })
                return self._parse_reviews(raw)

        available = self.list_tool_names()
        logger.warning(f"未找到评论工具，可用工具: {available}")
        return []

    def get_keyword_data(self, asin: str, site: str = "amazon.com") -> Optional[dict]:
        """获取关键词数据"""
        candidates = ["keyword_research", "keyword_asin", "asin_keywords",
                       "traffic_keyword", "keyword_analysis"]

        for name in candidates:
            if name in self._tools:
                raw = self.call_tool(name, {"asin": asin, "site": site})
                return self._parse_json(raw)

        return None

    @staticmethod
    def _parse_json(raw: str) -> dict:
        if isinstance(raw, dict):
            return raw
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {"raw": raw}

    @staticmethod
    def _parse_reviews(raw: str) -> List[str]:
        data = SellerspriteClient._parse_json(raw)
        if isinstance(data, list):
            return data if all(isinstance(i, str) for i in data) else [
                str(i) for i in data
            ]
        if isinstance(data, dict):
            for key in ("reviews", "items", "data", "list"):
                if key in data and isinstance(data[key], list):
                    items = data[key]
                    return [
                        item.get("content") or item.get("text") or item.get("body") or str(item)
                        for item in items
                    ]
        if isinstance(raw, str):
            return [raw]
        return []
