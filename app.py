import streamlit as st
import pandas as pd
from sellersprite_client import SellerspriteClient
from analyzer import ReviewAnalyzer
import time

# Page config
st.set_page_config(
    page_title="竞品评论智能分析工具",
    page_icon="🔍",
    layout="wide"
)

# Title
st.title("🔍 竞品评论智能分析工具")
st.markdown("输入竞品 ASIN，自动拉取评论并通过 AI 分析痛点，输出结构化分析报告。")

# Sidebar for settings
with st.sidebar:
    st.header("⚙️ 设置")
    
    # API Key inputs (with fallback to secrets)
    sellersprite_api_key = st.text_input(
        "卖家精灵 API Key",
        type="password",
        value=st.secrets.get("SELLERSPRITE_API_KEY", ""),
        help="从卖家精灵后台获取 API Key"
    )
    
    deepseek_api_key = st.text_input(
        "DeepSeek API Key",
        type="password",
        value=st.secrets.get("DEEPSEEK_API_KEY", ""),
        help="DeepSeek API Key（已配置则自动填充）"
    )
    
    st.markdown("---")
    st.markdown("### 使用说明")
    st.markdown("""
    1. 输入竞品 ASIN（如 B08N5WRWNW）
    2. 选择目标站点
    3. 点击「开始分析」
    4. 等待系统拉取评论并 AI 分析
    5. 查看结构化报告
    """)

# Main input area
col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    asin = st.text_input("竞品 ASIN", placeholder="例如: B08N5WRWNW", help="输入 Amazon 商品的标准 ASIN")

with col2:
    site = st.selectbox(
        "站点",
        options=["amazon.com", "amazon.co.uk", "amazon.de", "amazon.fr", "amazon.it", "amazon.es", "amazon.ca", "amazon.jp"],
        index=0,
        help="选择目标 Amazon 站点"
    )

with col3:
    max_reviews = st.number_input("最大评论数", min_value=10, max_value=500, value=100, step=10, help="限制分析的评论数量")

# Optional: manual review input
with st.expander("📝 手动粘贴评论样本（可选）"):
    st.markdown("如果卖家精灵 API 无法获取评论，可以手动粘贴评论内容进行分析。")
    manual_reviews = st.text_area(
        "评论内容（每行一条评论）",
        height=200,
        placeholder="粘贴评论内容，每行一条..."
    )

# Analyze button
analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)

# Analysis logic
if analyze_button:
    if not asin:
        st.error("❌ 请输入 ASIN")
        st.stop()
    
    if not sellersprite_api_key:
        st.error("❌ 请提供卖家精灵 API Key")
        st.stop()
    
    if not deepseek_api_key:
        st.error("❌ 请提供 DeepSeek API Key")
        st.stop()
    
    # Initialize clients
    sellersprite = SellerspriteClient(api_key=sellersprite_api_key)
    analyzer = ReviewAnalyzer(api_key=deepseek_api_key)
    
    # Progress bar
    progress_bar = st.progress(0, text="初始化...")
    status_text = st.empty()
    
    try:
        # Step 1: Fetch reviews
        status_text.text("📥 正在从卖家精灵获取评论数据...")
        progress_bar.progress(10, text="获取评论数据中...")
        
        reviews = []
        if manual_reviews.strip():
            # Use manual reviews if provided
            reviews = [r.strip() for r in manual_reviews.split("\n") if r.strip()]
            st.info(f"使用手动粘贴的 {len(reviews)} 条评论进行分析")
        else:
            # Try to fetch from sellersprite
            try:
                reviews = sellersprite.get_reviews(asin=asin, site=site, max_reviews=max_reviews)
                if not reviews:
                    st.warning("⚠️ 卖家精灵未返回评论数据，请尝试手动粘贴评论。")
                    st.stop()
                st.success(f"成功获取 {len(reviews)} 条评论")
            except Exception as e:
                st.warning(f"⚠️ 卖家精灵 API 调用失败: {str(e)}")
                st.info("💡 请手动粘贴评论样本后重新分析。")
                st.stop()
        
        progress_bar.progress(30, text="评论数据获取完成")
        
        # Step 2: Analyze reviews
        status_text.text("🧠 AI 正在分析评论痛点...")
        progress_bar.progress(50, text="AI 分析中...")
        
        # If too many reviews, summarize
        if len(reviews) > 200:
            st.info(f"评论数量较多 ({len(reviews)} 条)，将进行分批分析以避免超 token 限制。")
            # Split into batches
            batch_size = 50
            all_analysis = []
            for i in range(0, len(reviews), batch_size):
                batch = reviews[i:i+batch_size]
                batch_analysis = analyzer.analyze_reviews(batch)
                all_analysis.append(batch_analysis)
                progress = 50 + int((i + batch_size) / len(reviews) * 40)
                progress_bar.progress(min(progress, 90), text=f"分析批次 {i//batch_size + 1}/{(len(reviews)-1)//batch_size + 1}")
            # Merge analysis
            report = analyzer.merge_analysis(all_analysis)
        else:
            report = analyzer.analyze_reviews(reviews)
        
        progress_bar.progress(90, text="AI 分析完成")
        
        # Step 3: Display report
        status_text.text("📊 生成分析报告...")
        progress_bar.progress(100, text="完成！")
        
        st.success("✅ 分析完成！")
        
        # Display report sections
        st.header("📊 竞品评论分析报告")
        
        # 1. Product defects
        st.subheader("1. 产品缺陷归类")
        if "defects" in report:
            defects_df = pd.DataFrame(report["defects"])
            if not defects_df.empty:
                st.dataframe(defects_df, use_container_width=True)
            else:
                st.info("暂无缺陷数据")
        else:
            st.info("暂无缺陷数据")
        
        # 2. Sentiment analysis
        st.subheader("2. 买家情绪分析")
        if "sentiment" in report:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("正面情绪", f"{report['sentiment'].get('positive', 0)}%")
            with col2:
                st.metric("负面情绪", f"{report['sentiment'].get('negative', 0)}%")
            st.markdown("**核心不满点：**")
            for point in report["sentiment"].get("pain_points", []):
                st.markdown(f"- {point}")
        else:
            st.info("暂无情绪数据")
        
        # 3. Opportunity mining
        st.subheader("3. 竞品机会挖掘")
        if "opportunities" in report:
            for opp in report["opportunities"]:
                st.markdown(f"- **{opp.get('title', '')}**: {opp.get('description', '')}")
        else:
            st.info("暂无机会数据")
        
        # 4. Improvement suggestions
        st.subheader("4. 改进建议（按优先级排序）")
        if "improvements" in report:
            for i, imp in enumerate(report["improvements"], 1):
                st.markdown(f"**{i}. {imp.get('title', '')}**")
                st.markdown(f"   - 优先级: {imp.get('priority', '中')}")
                st.markdown(f"   - 操作建议: {imp.get('action', '')}")
        else:
            st.info("暂无改进建议")
        
        # 5. Original review excerpts
        st.subheader("5. 原始评论摘要")
        if "excerpts" in report:
            for excerpt in report["excerpts"]:
                st.markdown(f"**原文：** {excerpt.get('original', '')}")
                st.markdown(f"**翻译：** {excerpt.get('translation', '')}")
                st.markdown("---")
        else:
            st.info("暂无评论摘要")
        
        # Download button
        report_text = str(report)
        st.download_button(
            label="📥 下载分析报告 (JSON)",
            data=report_text,
            file_name=f"review_analysis_{asin}_{site}.json",
            mime="application/json"
        )
        
    except Exception as e:
        st.error(f"❌ 分析过程中出现错误: {str(e)}")
        st.exception(e)
    finally:
        progress_bar.empty()
        status_text.empty()

# Footer
st.markdown("---")
st.markdown("💡 本工具使用卖家精灵 API 获取评论数据，DeepSeek AI 进行语义分析。")
