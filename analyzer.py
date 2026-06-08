import json
import re
import logging
import urllib.request
import urllib.error
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ReviewAnalyzer:
    """使用 DeepSeek API 分析评论痛点"""

    API_URL = "https://api.deepseek.com/v1/chat/completions"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _chunk_reviews(self, reviews: List[str], max_chars: int = 3000) -> List[str]:
        """将评论分块，避免超 token 限制"""
        chunks = []
        current_chunk = []
        current_length = 0

        for review in reviews:
            review_len = len(review)
            if current_length + review_len > max_chars and current_chunk:
                chunks.append("\n---\n".join(current_chunk))
                current_chunk = [review]
                current_length = review_len
            else:
                current_chunk.append(review)
                current_length += review_len

        if current_chunk:
            chunks.append("\n---\n".join(current_chunk))

        return chunks or ["\n---\n".join(reviews)]

    def _call_deepseek(self, system_prompt: str, user_message: str) -> str:
        """调用 DeepSeek API"""
        payload = json.dumps({
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }).encode("utf-8")

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            raise ConnectionError(f"DeepSeek API 调用失败 [{e.code}]: {err_body}")

    def _safe_parse_json(self, text: str) -> dict:
        """安全解析 AI 返回的 JSON，处理 markdown 包裹等情况"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法解析 AI 返回的 JSON: {text[:300]}...")

    def analyze_reviews(self, reviews: List[str], asin: str, site: str) -> Dict[str, Any]:
        """分析评论并返回结构化报告"""
        empty_report = {
            "defect_classification": [],
            "sentiment": {"positive_pct": 0, "negative_pct": 0, "core_complaints": []},
            "opportunities": [],
            "improvements": [],
            "review_summary": []
        }

        if not reviews:
            return empty_report

        chunks = self._chunk_reviews(reviews)

        system_prompt = """你是一个专业的亚马逊产品分析专家。请分析以下买家评论（主要是1-3星差评），输出结构化的JSON报告。

请严格按照以下JSON格式输出，不要包含其他内容：
{
  "defect_classification": [
    {"category": "质量", "count": 5, "examples": ["评论原文摘录1", "评论原文摘录2"]}
  ],
  "sentiment": {
    "positive_pct": 10,
    "negative_pct": 90,
    "core_complaints": ["核心不满点1", "核心不满点2"]
  },
  "opportunities": [
    {"title": "改进方向", "description": "详细说明，为什么这是一个机会"}
  ],
  "improvements": [
    {"priority": "高", "suggestion": "改进建议", "action": "具体操作步骤"}
  ],
  "review_summary": [
    {"original": "英文原文", "translation": "中文翻译"}
  ]
}

注意：
- defect_classification 的 category 可选：质量、尺寸、材质、功能、包装、物流、客服、其他
- sentiment 百分比为整数
- review_summary 最多选5条最有代表性的差评
- 所有内容使用中文"""

        if len(chunks) == 1:
            user_message = f"ASIN: {asin}\n站点: {site}\n\n评论内容：\n{chunks[0]}"
            result_text = self._call_deepseek(system_prompt, user_message)
            try:
                return self._safe_parse_json(result_text)
            except ValueError:
                return {**empty_report, "raw_analysis": result_text}

        partial_results = []
        for i, chunk in enumerate(chunks):
            user_message = f"ASIN: {asin}\n站点: {site}\n\n这是第 {i+1}/{len(chunks)} 批评论：\n{chunk}"
            result_text = self._call_deepseek(system_prompt, user_message)
            try:
                partial_results.append(self._safe_parse_json(result_text))
            except ValueError:
                logger.warning(f"第 {i+1} 批分析结果解析失败")

        return self._merge_results(partial_results) if partial_results else empty_report

    def _merge_results(self, results: List[Dict]) -> Dict:
        """合并多批分析结果"""
        merged = {
            "defect_classification": [],
            "sentiment": {"positive_pct": 0, "negative_pct": 0, "core_complaints": []},
            "opportunities": [],
            "improvements": [],
            "review_summary": []
        }

        if not results:
            return merged

        # 合并缺陷分类
        category_map: Dict[str, dict] = {}
        for r in results:
            for defect in r.get("defect_classification", []):
                cat = defect["category"]
                if cat in category_map:
                    category_map[cat]["count"] += defect["count"]
                    category_map[cat]["examples"].extend(defect.get("examples", []))
                else:
                    category_map[cat] = {
                        "category": cat,
                        "count": defect["count"],
                        "examples": list(defect.get("examples", []))
                    }
        merged["defect_classification"] = list(category_map.values())

        # 情绪取平均
        cnt = len(results)
        merged["sentiment"]["positive_pct"] = round(
            sum(r.get("sentiment", {}).get("positive_pct", 0) for r in results) / cnt, 1
        )
        merged["sentiment"]["negative_pct"] = round(
            sum(r.get("sentiment", {}).get("negative_pct", 0) for r in results) / cnt, 1
        )

        # 核心不满点去重
        seen = set()
        all_complaints = []
        for r in results:
            for c in r.get("sentiment", {}).get("core_complaints", []):
                if c not in seen:
                    all_complaints.append(c)
                    seen.add(c)
        merged["sentiment"]["core_complaints"] = all_complaints

        # 合并机会 & 改进（按 title/suggestion 去重）
        seen_opp = set()
        seen_imp = set()
        for r in results:
            for opp in r.get("opportunities", []):
                key = opp.get("title", "")
                if key not in seen_opp:
                    merged["opportunities"].append(opp)
                    seen_opp.add(key)
            for imp in r.get("improvements", []):
                key = imp.get("suggestion", "")
                if key not in seen_imp:
                    merged["improvements"].append(imp)
                    seen_imp.add(key)

        # 评论摘要取前5条
        for r in results:
            merged["review_summary"].extend(r.get("review_summary", []))
        merged["review_summary"] = merged["review_summary"][:5]

        return merged
