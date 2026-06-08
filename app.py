import streamlit as st
import pandas as pd
import time
from sellersprite_client import SellerspriteClient
from analyzer import ReviewAnalyzer

# Page config
st.set_page_config(
    page_title="竞品评论智能分析工具",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 竞品评论智能分析工具")
st.markdown("输入竞品 ASIN，自动拉取差评并通过 AI 分析痛点，输出结构化分析报告。")

# Sidebar for API keys
with st.sidebar:
    st.header("⚙️ 配置")
    sellersprite_api_key = st.text_input(
        "卖家精灵 API Key",
        type="password",
        help="从卖家精灵后台获取 API Key",
        value=st.secrets.get("SELLERSPRITE_API_KEY", "")
    )
    deepseek_api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        help="复用已有的 DEEPSEEK_API_KEY",
        value=st.secrets.get("DEEPSEEK_API_KEY", "")
    )
    st.markdown("---")
    st.markdown("### 使用说明")
    st.markdown("""
    1. 输入竞品 ASIN
    2. 选择亚马逊站点
    3. 点击「开始分析」
    4. 等待 AI 分析完成
    """)

# Main input area
col1, col2, col3 = st.columns([3, 2, 1])
with col1:
    asin = st.text_input("竞品 ASIN", placeholder="例如: B08N5WRWNW", help="输入亚马逊标准识别码")
with col2:
    site = st.selectbox(
        "亚马逊站点",
        options=["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.it", "amazon.es", "amazon.ca", "amazon.com.au"],
        index=0
    )
with col3:
    max_reviews = st.number_input("最大评论数", min_value=10, max_value=500, value=100, step=10)

# Optional manual review input
with st.expander("📝 手动粘贴评论样本（可选）"):
    st.markdown("如果卖家精灵无法直接获取评论，可以手动粘贴 1-3 星评论内容，每行一条。")
    manual_reviews = st.text_area("评论内容", height=200, placeholder="每条评论一行，支持中英文")

# Analyze button
if st.button("🚀 开始分析", type="primary", use_container_width=True):
    if not asin:
        st.error("请输入 ASIN")
        st.stop()
    if not sellersprite_api_key:
        st.error("请提供卖家精灵 API Key")
        st.stop()
    if not deepseek_api_key:
        st.error("请提供 DeepSeek API Key")
        st.stop()

    # Progress bar
    progress_bar = st.progress(0, text="初始化...")
    status_text = st.empty()

    try:
        # Step 1: Fetch reviews from Sellersprite
        status_text.text("🔄 正在从卖家精灵获取评论数据...")
        progress_bar.progress(20, text="获取评论数据中...")
        
        client = SellerspriteClient(api_key=sellersprite_api_key)
        
        if manual_reviews.strip():
            # Use manual reviews
            review_texts = [r.strip() for r in manual_reviews.split("\n") if r.strip()]
            status_text.text(f"✅ 已加载 {len(review_texts)} 条手动评论")
        else:
            # Fetch from API
            review_texts = client.get_reviews(asin, site, max_reviews=max_reviews)
            if not review_texts:
                # Fallback: try to get product info and ask user to paste reviews
                st.warning("⚠️ 卖家精灵未直接返回评论数据，请手动粘贴评论样本后重试。")
                st.info("💡 提示：您可以在上方展开「手动粘贴评论样本」区域，粘贴 1-3 星评论内容。")
                st.stop()
            status_text.text(f"✅ 成功获取 {len(review_texts)} 条评论")
        
        progress_bar.progress(50, text="评论数据获取完成")
        
        # Step 2: AI Analysis
        status_text.text("🧠 AI 正在分析评论痛点...")
        progress_bar.progress(60, text="AI 分析中...")
        
        analyzer = ReviewAnalyzer(api_key=deepseek_api_key)
        report = analyzer.analyze_reviews(review_texts, asin, site)
        
        progress_bar.progress(90, text="生成报告中...")
        
        # Step 3: Display report
        status_text.text("✅ 分析完成！")
        progress_bar.progress(100, text="完成")
        
        # Display results
        st.success("🎉 分析完成！")
        
        # Report sections
        st.header("📊 分析报告")
        
        # 1. Product defect classification
        st.subheader("1. 产品缺陷归类")
        if "defect_classification" in report:
            defect_df = pd.DataFrame(report["defect_classification"])
            st.dataframe(defect_df, use_container_width=True)
        else:
            st.write(report.get("defect_classification_text", "暂无数据"))
        
        # 2. Sentiment analysis
        st.subheader("2. 买家情绪分析")
        if "sentiment" in report:
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("正面情绪占比", f"{report['sentiment'].get('positive_pct', 0):.1f}%")
            with col_b:
                st.metric("负面情绪占比", f"{report['sentiment'].get('negative_pct', 0):.1f}%")
            st.markdown("**核心不满点：**")
            for point in report["sentiment"].get("core_complaints", []):
                st.markdown(f"- {point}")
        else:
            st.write(report.get("sentiment_text", "暂无数据"))
        
        # 3. Opportunity mining
        st.subheader("3. 竞品机会挖掘")
        if "opportunities" in report:
            for opp in report["opportunities"]:
                st.markdown(f"- **{opp.get('title', '')}**: {opp.get('description', '')}")
        else:
            st.write(report.get("opportunities_text", "暂无数据"))
        
        # 4. Improvement suggestions
        st.subheader("4. 改进建议（按优先级排序）")
        if "improvements" in report:
            for i, imp in enumerate(report["improvements"], 1):
                st.markdown(f"**{i}. {imp.get('priority', '')}** - {imp.get('suggestion', '')}")
                if imp.get("action"):
                    st.markdown(f"   💡 操作建议：{imp['action']}")
        else:
            st.write(report.get("improvements_text", "暂无数据"))
        
        # 5. Original review summary
        st.subheader("5. 原始评论摘要")
        if "review_summary" in report:
            for rev in report["review_summary"]:
                st.markdown(f"- **原文**: {rev.get('original', '')}")
                if rev.get("translation"):
                    st.markdown(f"  📝 **翻译**: {rev['translation']}")
                st.markdown("---")
        else:
            st.write(report.get("review_summary_text", "暂无数据"))
        
        # Download button
        report_json = str(report)
        st.download_button(
            label="📥 下载报告 (JSON)",
            data=report_json,
            file_name=f"review_analysis_{asin}_{site}.json",
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"❌ 分析过程中出现错误: {str(e)}")
        st.exception(e)
    finally:
        time.sleep(1)
        progress_bar.empty()
        status_text.empty()

# Footer
st.markdown("---")
st.markdown("💡 本工具使用 AI 分析评论，结果仅供参考，建议结合人工判断。")
