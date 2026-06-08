import json
import logging
from typing import List, Dict, Any
import requests

logger = logging.getLogger(__name__)

class ReviewAnalyzer:
    """
    使用 DeepSeek API 分析评论痛点
    """
    
    API_URL = "https://api.deepseek.com/v1/chat/completions"
    MAX_TOKENS_PER_REQUEST = 4000  # 控制每次请求的 token 数
    
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
        
        return chunks
    
    def _call_deepseek(self, system_prompt: str, user_message: str) -> str:
        """调用 DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API 调用失败: {e}")
            raise
    
    def analyze_reviews(self, reviews: List[str], asin: str, site: str) -> Dict[str, Any]:
        """
        分析评论并返回结构化报告
        
        返回格式:
        {
            "defect_classification": [...],
            "sentiment": {...},
            "opportunities": [...],
            "improvements": [...],
            "review_summary": [...]
        }
        """
        if not reviews:
            return {
                "defect_classification": [],
                "sentiment": {"positive_pct": 0, "negative_pct": 0, "core_complaints": []},
                "opportunities": [],
                "improvements": [],
                "review_summary": []
            }
        
        # 分块处理
        chunks = self._chunk_reviews(reviews)
        
        system_prompt = """你是一个专业的亚马逊产品分析专家。请分析以下买家评论（主要是1-3星差评），输出结构化的JSON报告。

请严格按照以下JSON格式输出，不要包含其他内容：
{
  "defect_classification": [
    {"category": "质量", "count": 5, "examples": ["评论原文摘录1", "评论原文摘录2"]},
    {"category": "尺寸", "count": 3, "examples": [...]}
  ],
  "sentiment": {
    "positive_pct": 10,
    "negative_pct": 90,
    "core_complaints": ["核心不满点1", "核心不满点2"]
  },
  "opportunities": [
    {"title": "改进方向", "description": "详细说明"}
  ],
  "improvements": [
    {"priority": "高", "suggestion": "改进建议", "action": "具体操作"}
  ],
  "review_summary": [
    {"original": "原文", "translation": "中文翻译"}
  ]
}

注意：
- defect_classification 的 category 可选值：质量、尺寸、材质、功能、包装、物流、客服、其他
- sentiment 中的百分比为整数
- review_summary 最多选5条最有代表性的差评
- 所有内容使用中文"""
        
        # 如果评论量小，直接分析
        if len(chunks) == 1:
            user_message = f"ASIN: {asin}\n站点: {site}\n\n评论内容：\n{chunks[0]}"
            result_text = self._call_deepseek(system_prompt, user_message)
            try:
                # 尝试解析 JSON
                result = json.loads(result_text)
                return result
            except json.JSONDecodeError:
                # 如果返回的不是 JSON，尝试提取 JSON 部分
                import re
                json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        return result
                    except:
                        pass
                # 返回原始文本
                return {
                    "defect_classification": [],
                    "sentiment": {"positive_pct": 0, "negative_pct": 0, "core_complaints": []},
                    "opportunities": [],
                    "improvements": [],
                    "review_summary": [],
                    "raw_analysis": result_text
                }
        else:
            # 多块分析，先分别分析再汇总
            partial_results = []
            for i, chunk in enumerate(chunks):
                user_message = f"ASIN: {asin}\n站点: {site}\n\n这是第 {i+1}/{len(chunks)} 批评论：\n{chunk}"
                result_text = self._call_deepseek(system_prompt, user_message)
                try:
                    partial = json.loads(result_text)
                    partial_results.append(partial)
                except:
                    logger.warning(f"第 {i+1} 批分析结果解析失败，跳过")
            
            # 汇总结果
            return self._merge_results(partial_results)
    
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
        category_map = {}
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
                        "examples": defect.get("examples", [])
                    }
        merged["defect_classification"] = list(category_map.values())
        
        # 合并情绪分析（取平均）
        total_positive = sum(r.get("sentiment", {}).get("positive_pct", 0) for r in results)
        total_negative = sum(r.get("sentiment", {}).get("negative_pct", 0) for r in results)
        count = len(results)
        merged["sentiment"]["positive_pct"] = round(total_positive / count, 1) if count else 0
        merged["sentiment"]["negative_pct"] = round(total_negative / count, 1) if count else 0
        
        # 合并核心不满点（去重）
        all_complaints = []
        for r in results:
            all_complaints.extend(r.get("sentiment", {}).get("core_complaints", []))
        merged["sentiment"]["core_complaints"] = list(set(all_complaints))
        
        # 合并机会
        for r in results:
            merged["opportunities"].extend(r.get("opportunities", []))
        
        # 合并改进建议
        for r in results:
            merged["improvements"].extend(r.get("improvements", []))
        
        # 合并评论摘要（取前5条）
        for r in results:
            merged["review_summary"].extend(r.get("review_summary", []))
        merged["review_summary"] = merged["review_summary"][:5]
        
        return merged
