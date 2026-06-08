import json
import logging
from typing import List, Dict, Any
import requests

logger = logging.getLogger(__name__)

class ReviewAnalyzer:
    """
    AI 评论分析器，使用 DeepSeek API 进行语义分析
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
    
    def _call_deepseek(self, messages: List[Dict], max_tokens: int = 4000) -> str:
        """
        调用 DeepSeek API
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"DeepSeek API call failed: {e}")
            raise
    
    def analyze_reviews(self, reviews: List[str]) -> Dict[str, Any]:
        """
        分析评论列表，返回结构化报告
        """
        if not reviews:
            return {
                "defects": [],
                "sentiment": {"positive": 0, "negative": 0, "pain_points": []},
                "opportunities": [],
                "improvements": [],
                "excerpts": []
            }
        
        # Prepare the prompt
        reviews_text = "\n---\n".join([f"评论 {i+1}: {r}" for i, r in enumerate(reviews)])
        
        system_prompt = """你是一个专业的亚马逊产品评论分析专家。请分析以下评论，输出严格的 JSON 格式报告。

报告必须包含以下字段：
1. defects: 产品缺陷归类数组，每个元素包含 category（缺陷类别，如质量、尺寸、材质、功能、包装等）、count（频次）、examples（示例评论）
2. sentiment: 买家情绪分析对象，包含 positive（正面情绪百分比）、negative（负面情绪百分比）、pain_points（核心不满点数组）
3. opportunities: 竞品机会挖掘数组，每个元素包含 title（机会标题）、description（详细描述）
4. improvements: 改进建议数组，每个元素包含 title（建议标题）、priority（优先级：高/中/低）、action（具体操作建议）
5. excerpts: 原始评论摘要数组，每个元素包含 original（原文）、translation（中文翻译）

请确保输出是合法的 JSON 格式，不要包含其他文字。"""
        
        user_prompt = f"请分析以下亚马逊产品评论，输出结构化报告：\n\n{reviews_text}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self._call_deepseek(messages, max_tokens=4000)
            # Parse JSON from response
            # Try to find JSON in the response
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                report = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
            
            # Ensure all required fields exist
            required_fields = ["defects", "sentiment", "opportunities", "improvements", "excerpts"]
            for field in required_fields:
                if field not in report:
                    report[field] = [] if field != "sentiment" else {"positive": 0, "negative": 0, "pain_points": []}
            
            return report
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.debug(f"Raw response: {response}")
            # Return a basic report with the raw response
            return {
                "defects": [],
                "sentiment": {"positive": 0, "negative": 0, "pain_points": ["AI 分析结果解析失败，请查看原始输出"]},
                "opportunities": [],
                "improvements": [],
                "excerpts": [{"original": "AI 原始输出", "translation": response[:500]}]
            }
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
    
    def merge_analysis(self, analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        合并多个分析结果（用于分批分析）
        """
        if not analyses:
            return {
                "defects": [],
                "sentiment": {"positive": 0, "negative": 0, "pain_points": []},
                "opportunities": [],
                "improvements": [],
                "excerpts": []
            }
        
        if len(analyses) == 1:
            return analyses[0]
        
        # Merge defects
        all_defects = []
        defect_counts = {}
        for analysis in analyses:
            for defect in analysis.get("defects", []):
                cat = defect.get("category", "其他")
                if cat in defect_counts:
                    defect_counts[cat] += defect.get("count", 1)
                else:
                    defect_counts[cat] = defect.get("count", 1)
                    all_defects.append(defect)
        
        for defect in all_defects:
            defect["count"] = defect_counts.get(defect.get("category", "其他"), 0)
        
        # Merge sentiment (average)
        total_positive = sum(a.get("sentiment", {}).get("positive", 0) for a in analyses)
        total_negative = sum(a.get("sentiment", {}).get("negative", 0) for a in analyses)
        n = len(analyses)
        
        all_pain_points = []
        for a in analyses:
            all_pain_points.extend(a.get("sentiment", {}).get("pain_points", []))
        
        # Merge other fields (take unique)
        all_opportunities = []
        seen_opps = set()
        for a in analyses:
            for opp in a.get("opportunities", []):
                title = opp.get("title", "")
                if title not in seen_opps:
                    seen_opps.add(title)
                    all_opportunities.append(opp)
        
        all_improvements = []
        seen_imps = set()
        for a in analyses:
            for imp in a.get("improvements", []):
                title = imp.get("title", "")
                if title not in seen_imps:
                    seen_imps.add(title)
                    all_improvements.append(imp)
        
        all_excerpts = []
        seen_excerpts = set()
        for a in analyses:
            for ex in a.get("excerpts", []):
                orig = ex.get("original", "")
                if orig not in seen_excerpts:
                    seen_excerpts.add(orig)
                    all_excerpts.append(ex)
        
        return {
            "defects": all_defects,
            "sentiment": {
                "positive": round(total_positive / n, 1),
                "negative": round(total_negative / n, 1),
                "pain_points": all_pain_points[:10]  # Limit to top 10
            },
            "opportunities": all_opportunities,
            "improvements": all_improvements,
            "excerpts": all_excerpts[:20]  # Limit to 20 excerpts
        }
