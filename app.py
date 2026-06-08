import streamlit as st
import pandas as pd
import json
import time
from sellersprite_client import SellerspriteClient
from analyzer import ReviewAnalyzer

# 站点 → 卖家精灵 marketplace 编码
SITE_TO_MARKETPLACE = {
    "amazon.com": "US",
    "amazon.co.uk": "UK",
    "amazon.de": "DE",
    "amazon.fr": "FR",
    "amazon.it": "IT",
    "amazon.es": "ES",
    "amazon.ca": "CA",
    "amazon.com.au": "AU",
    "amazon.co.jp": "JP",
    "amazon.in": "IN",
    "amazon.com.mx": "MX",
    "amazon.com.br": "BR",
    "amazon.ae": "AE",
}

st.set_page_config(
    page_title="竞品评论智能分析工具",
    page_icon="\U0001f50d",
    layout="wide"
)

st.title("\U0001f50d 竞品评论智能分析工具")
st.markdown("输入竞品 ASIN，通过卖家精灵 MCP 拉取差评，AI 自动分析痛点并输出结构化报告。")

# ---- Sidebar ----
with st.sidebar:
    st.header("配置")
    sellersprite_api_key = st.text_input(
        "卖家精灵 MCP Key",
        type="password",
        help="从卖家精灵后台获取 secret-key",
        value=st.secrets.get("SELLERSPRITE_API_KEY", "")
    )
    deepseek_api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        help="用于 AI 语义分析",
        value=st.secrets.get("DEEPSEEK_API_KEY", "")
    )
    st.markdown("---")
    st.markdown("### 使用说明")
    st.markdown("""
    1. 填入两个 API Key
    2. 输入竞品 ASIN
    3. 选择亚马逊站点
    4. 点击「开始分析」
    5. 查看报告，支持下载
    """)
    st.markdown("---")
    st.caption("数据源: 卖家精灵 MCP")

# ---- Main ----
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    asin = st.text_input(
        "竞品 ASIN", placeholder="例如: B0BSHF7WHW",
        help="输入亚马逊标准识别码 (ASIN)"
    )
with col2:
    site = st.selectbox(
        "亚马逊站点",
        options=list(SITE_TO_MARKETPLACE.keys()),
        index=0
    )
with col3:
    max_reviews = st.number_input(
        "最大评论数", min_value=10, max_value=500, value=100, step=10
    )

with st.expander("手动粘贴评论样本（可选）"):
    st.markdown("如果 MCP 返回的评论不够，可手动粘贴 1-3 星差评，每行一条。")
    manual_reviews = st.text_area(
        "评论内容", height=200,
        placeholder="每条评论一行，支持中英文"
    )

# ---- Analyze ----
if st.button("开始分析", type="primary", use_container_width=True):
    if not asin:
        st.error("请输入 ASIN")
        st.stop()
    if not sellersprite_api_key:
        st.error("请在侧边栏填写卖家精灵 MCP Key")
        st.stop()
    if not deepseek_api_key:
        st.error("请在侧边栏填写 DeepSeek API Key")
        st.stop()

    marketplace = SITE_TO_MARKETPLACE[site]
    progress_bar = st.progress(0, text="初始化...")
    status_text = st.empty()

    try:
        # 1. 连接 MCP
        status_text.text("正在连接卖家精灵 MCP...")
        progress_bar.progress(10, text="连接 MCP 中...")

        client = SellerspriteClient(api_key=sellersprite_api_key)
        client.initialize()
        tools = client.discover_tools()
        status_text.text(f"MCP 已连接 ({len(tools)} 个工具可用)")

        # 2. 获取评论
        status_text.text("正在获取评论数据...")
        progress_bar.progress(30, text="获取评论中...")

        if manual_reviews.strip():
            review_texts = [r.strip() for r in manual_reviews.split("\n") if r.strip()]
            status_text.text(f"已加载 {len(review_texts)} 条手动评论")
        else:
            review_texts = client.get_review_texts(asin, marketplace, max_reviews=max_reviews)
            if not review_texts:
                # 尝试获取产品信息
                product = client.get_product_info(asin, marketplace)
                if product and "error" not in product:
                    title = product.get("title", "N/A")
                    st.info(f"已找到产品「{title}」，但暂无差评数据。请在下方手动粘贴差评内容。")
                    st.json({k: product[k] for k in ["asin", "title", "price", "rating", "brand"] if k in product})
                else:
                    st.warning("该 ASIN 暂无评论数据，请手动粘贴评论样本。")
                st.stop()
            status_text.text(f"成功获取 {len(review_texts)} 条评论")

        progress_bar.progress(50, text="评论数据获取完成")

        # 3. AI 分析
        status_text.text("AI 正在分析评论痛点...")
        progress_bar.progress(60, text="AI 分析中...")

        analyzer = ReviewAnalyzer(api_key=deepseek_api_key)
        report = analyzer.analyze_reviews(review_texts, asin, site)

        progress_bar.progress(90, text="生成报告中...")
        status_text.text("分析完成!")
        progress_bar.progress(100, text="完成")

        # ---- 展示报告 ----
        st.success("分析完成!")
        st.header("分析报告")

        # 1. 缺陷归类
        st.subheader("1. 产品缺陷归类")
        if report.get("defect_classification"):
            df = pd.DataFrame(report["defect_classification"])
            st.dataframe(df, use_container_width=True)
        else:
            st.write(report.get("defect_classification_text", "暂无数据"))

        # 2. 情绪分析
        st.subheader("2. 买家情绪分析")
        sentiment = report.get("sentiment", {})
        if sentiment:
            ca, cb = st.columns(2)
            with ca:
                st.metric("正面情绪占比", f"{sentiment.get('positive_pct', 0):.1f}%")
            with cb:
                st.metric("负面情绪占比", f"{sentiment.get('negative_pct', 0):.1f}%")
            if sentiment.get("core_complaints"):
                st.markdown("**核心不满点：**")
                for p in sentiment["core_complaints"]:
                    st.markdown(f"- {p}")
        else:
            st.write(report.get("sentiment_text", "暂无数据"))

        # 3. 竞品机会
        st.subheader("3. 竞品机会挖掘")
        if report.get("opportunities"):
            for opp in report["opportunities"]:
                title = opp.get("title", "")
                desc = opp.get("description", "")
                st.markdown(f"- **{title}**: {desc}")
        else:
            st.write(report.get("opportunities_text", "暂无数据"))

        # 4. 改进建议
        st.subheader("4. 改进建议（按优先级排序）")
        if report.get("improvements"):
            for i, imp in enumerate(report["improvements"], 1):
                priority = imp.get("priority", "")
                suggestion = imp.get("suggestion", "")
                action = imp.get("action", "")
                st.markdown(f"**{i}. [{priority}] {suggestion}**")
                if action:
                    st.markdown(f"  {action}")
        else:
            st.write(report.get("improvements_text", "暂无数据"))

        # 5. 评论摘要
        st.subheader("5. 原始评论摘要")
        if report.get("review_summary"):
            for rev in report["review_summary"]:
                st.markdown(f"- **原文**: {rev.get('original', '')}")
                if rev.get("translation"):
                    st.markdown(f"  **翻译**: {rev['translation']}")
                st.markdown("---")
        else:
            st.write(report.get("review_summary_text", "暂无数据"))

        # 下载
        st.download_button(
            label="下载报告 (JSON)",
            data=json.dumps(report, ensure_ascii=False, indent=2),
            file_name=f"review_analysis_{asin}.json",
            mime="application/json"
        )

    except ConnectionError as e:
        st.error(f"MCP 连接失败: {e}")
        st.info("请检查卖家精灵 MCP Key 是否正确。")
    except Exception as e:
        st.error(f"分析过程出错: {e}")
    finally:
        time.sleep(0.5)
        try:
            progress_bar.empty()
            status_text.empty()
        except Exception:
            pass

st.markdown("---")
st.caption("本工具使用 AI 分析评论，结果仅供参考，建议结合人工判断。")
