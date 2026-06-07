"""
单元测试 - ASIN 评论分析核心功能
"""

import sys
import os
import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import get_reviews, analyze_with_deepseek, format_report, MOCK_REVIEWS, DEFAULT_ASIN


class TestGetReviews:
    """测试 get_reviews 函数"""

    def test_existing_asin(self):
        """测试存在的 ASIN 返回评论列表"""
        reviews = get_reviews("B08N5WRWNW")
        assert isinstance(reviews, list)
        assert len(reviews) > 0
        for review in reviews:
            assert "rating" in review
            assert "title" in review
            assert "text" in review
            assert review["rating"] <= 3  # 确保只返回 1-3 星

    def test_non_existing_asin(self):
        """测试不存在的 ASIN 返回空列表"""
        reviews = get_reviews("INVALID_ASIN_123")
        assert isinstance(reviews, list)
        assert len(reviews) == 0

    def test_empty_asin(self):
        """测试空字符串 ASIN"""
        reviews = get_reviews("")
        assert isinstance(reviews, list)
        assert len(reviews) == 0

    def test_all_reviews_are_low_rating(self):
        """测试所有返回的评论都是 1-3 星"""
        for asin in MOCK_REVIEWS.keys():
            reviews = get_reviews(asin)
            for review in reviews:
                assert review["rating"] <= 3


class TestAnalyzeWithDeepseek:
    """测试 analyze_with_deepseek 函数"""

    def test_with_reviews(self):
        """测试有评论时返回分析报告"""
        reviews = [
            {"rating": 1, "title": "测试标题", "text": "测试内容"}
        ]
        result = analyze_with_deepseek(reviews)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "痛点分析报告" in result

    def test_with_empty_reviews(self):
        """测试空评论列表返回提示信息"""
        result = analyze_with_deepseek([])
        assert isinstance(result, str)
        assert "未找到" in result

    def test_with_multiple_reviews(self):
        """测试多条评论时分析包含所有评论"""
        reviews = [
            {"rating": 1, "title": "问题1", "text": "内容1"},
            {"rating": 2, "title": "问题2", "text": "内容2"},
            {"rating": 3, "title": "问题3", "text": "内容3"}
        ]
        result = analyze_with_deepseek(reviews)
        assert "3 条" in result  # 应该提到评论数量


class TestFormatReport:
    """测试 format_report 函数"""

    def test_basic_formatting(self):
        """测试基本格式化"""
        raw = "测试报告内容"
        result = format_report(raw)
        assert result == raw.strip()

    def test_with_whitespace(self):
        """测试去除首尾空白"""
        raw = "  \n  带空白的报告  \n  "
        result = format_report(raw)
        assert result == "带空白的报告"

    def test_empty_string(self):
        """测试空字符串"""
        result = format_report("")
        assert result == ""


class TestMockDataIntegrity:
    """测试模拟数据完整性"""

    def test_mock_reviews_structure(self):
        """测试模拟数据结构正确"""
        for asin, reviews in MOCK_REVIEWS.items():
            assert isinstance(asin, str)
            assert len(asin) > 0
            assert isinstance(reviews, list)
            for review in reviews:
                assert "rating" in review
                assert "title" in review
                assert "text" in review
                assert isinstance(review["rating"], int)
                assert 1 <= review["rating"] <= 5

    def test_default_asin_exists(self):
        """测试默认 ASIN 在模拟数据中"""
        assert DEFAULT_ASIN in MOCK_REVIEWS


if __name__ == "__main__":
    pytest.main(["-v", __file__])
