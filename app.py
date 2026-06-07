#!/usr/bin/env python3
"""
Amazon Review Insight - ASIN 评论分析核心功能

用户输入 Amazon ASIN，输出 1-3 星差评中的用户痛点分析报告。
"""

import sys
import json
import os
from typing import Dict, List, Optional

# 尝试导入 dotenv 用于环境变量管理（可选）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 模拟评论数据（用于演示，无需真实抓取）
MOCK_REVIEWS = {
    "B08N5WRWNW": [
        {"rating": 1, "title": "完全不防水", "text": "用了不到一周就进水了，屏幕起雾，完全不能用了。宣传说防水，实际根本不行。"},
        {"rating": 1, "title": "电池太差", "text": "充满电只能用2小时，和宣传的8小时差太远。退货了。"},
        {"rating": 2, "title": "音质一般", "text": "低音几乎没有，高音刺耳。这个价位不如买其他品牌。"},
        {"rating": 2, "title": "佩戴不舒服", "text": "戴半小时耳朵就疼，耳塞太大，不适合小耳道。"},
        {"rating": 3, "title": "连接不稳定", "text": "蓝牙经常断连，尤其是放在口袋的时候。需要频繁重新配对。"},
        {"rating": 3, "title": "充电口容易坏", "text": "用了两个月充电口就松了，接触不良。"},
        {"rating": 1, "title": "客服态度差", "text": "出现问题找客服，半天不回复，最后说不能退换。差评。"},
        {"rating": 2, "title": "做工粗糙", "text": "塑料感很强，接缝处有毛刺，不像几百块的东西。"},
    ],
    "B09G9D7K6S": [
        {"rating": 1, "title": "屏幕有坏点", "text": "收到就有两个坏点，在屏幕中间，非常影响使用。"},
        {"rating": 2, "title": "系统卡顿", "text": "打开应用要等很久，切换界面也卡，不如老款流畅。"},
        {"rating": 3, "title": "续航缩水", "text": "官方说12小时，实际重度使用只有6-7小时。"},
        {"rating": 1, "title": "充电慢", "text": "支持快充但实际充电速度很慢，充满要3小时。"},
        {"rating": 2, "title": "摄像头凸起", "text": "平放时翘起，打字会晃动，而且容易刮花。"},
        {"rating": 3, "title": "指纹收集器", "text": "背面玻璃太容易沾指纹，看起来脏兮兮的。"},
    ],
}

# 默认 ASIN 用于演示
DEFAULT_ASIN = "B08N5WRWNW"


def get_reviews(asin: str) -> List[Dict[str, str]]:
    """
    获取指定 ASIN 的 1-3 星评论。
    当前使用模拟数据，后续可替换为真实抓取。
    """
    reviews = MOCK_REVIEWS.get(asin)
    if reviews is None:
        # 如果 ASIN 不在模拟数据中，返回空列表
        return []
    # 只返回 1-3 星评论（模拟数据已过滤）
    return [r for r in reviews if r["rating"] <= 3]


def analyze_with_deepseek(reviews: List[Dict[str, str]]) -> str:
    """
    使用 DeepSeek API 分析评论痛点。
    当前使用模拟分析，后续可替换为真实 API 调用。
    """
    # 模拟 DeepSeek 分析结果
    if not reviews:
        return "未找到该 ASIN 的 1-3 星评论数据。"

    # 提取所有评论文本
    review_texts = [f"[{r['rating']}星] {r['title']}: {r['text']}" for r in reviews]
    combined = "\n".join(review_texts)

    # 模拟 AI 分析（实际应调用 API）
    analysis = f"""
## 痛点分析报告

### 分析概述
共分析 {len(reviews)} 条 1-3 星评论，识别出以下核心痛点：

### 1. 产品质量问题
- **防水性能不足**：部分用户反映产品不防水，与宣传不符。
- **做工粗糙**：塑料感强，接缝有毛刺，影响使用体验。
- **屏幕/充电口易损**：使用一段时间后出现坏点或接触不良。

### 2. 性能与续航
- **电池续航虚标**：实际使用时间远低于宣传值。
- **连接稳定性差**：蓝牙频繁断连，影响日常使用。
- **系统卡顿**：应用启动慢，界面切换不流畅。

### 3. 用户体验
- **佩戴/握持不舒适**：人体工学设计不佳，长时间使用不适。
- **充电速度慢**：不支持快充或实际充电效率低。
- **易沾指纹**：外观材质选择不当。

### 4. 售后服务
- **客服响应慢**：问题反馈后处理不及时。
- **退换货困难**：售后政策不友好。

### 改进建议
1. 加强防水测试，确保宣传与实际一致。
2. 优化电池管理系统，提升续航表现。
3. 改进人体工学设计，提升佩戴舒适度。
4. 升级蓝牙芯片，增强连接稳定性。
5. 完善售后服务体系，提高客户满意度。
"""
    return analysis


def format_report(analysis: str) -> str:
    """格式化输出报告"""
    return analysis.strip()


def main():
    """主函数"""
    print("=" * 50)
    print("Amazon Review Insight - ASIN 评论分析工具")
    print("=" * 50)
    print()

    # 获取用户输入的 ASIN
    asin = input("请输入 Amazon ASIN（例如 B08N5WRWNW）: ").strip()
    if not asin:
        print("ASIN 不能为空，使用默认 ASIN 演示。")
        asin = DEFAULT_ASIN

    print(f"\n正在分析 ASIN: {asin} ...")
    print()

    # 获取评论
    reviews = get_reviews(asin)
    if not reviews:
        print(f"未找到 ASIN {asin} 的 1-3 星评论数据。")
        print("提示：当前使用模拟数据，支持的 ASIN 包括：")
        for key in MOCK_REVIEWS.keys():
            print(f"  - {key}")
        sys.exit(1)

    print(f"找到 {len(reviews)} 条 1-3 星评论。")
    print()

    # 分析痛点
    print("正在生成分析报告...")
    analysis = analyze_with_deepseek(reviews)
    report = format_report(analysis)

    # 输出报告
    print()
    print("=" * 50)
    print(report)
    print("=" * 50)


if __name__ == "__main__":
    main()
