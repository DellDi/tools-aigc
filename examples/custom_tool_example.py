"""
自定义工具示例 - 演示如何创建和注册自定义工具
"""

import asyncio
import logging
import random
from typing import List, Optional

from app.tools.base import BaseTool, ToolRegistry, ToolResult


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class RandomNumberTool(BaseTool):
    """生成随机数的工具"""

    name = "random_number"
    description = "生成指定范围内的随机数"

    # 参数描述
    _min_description = "随机数的最小值（包含）"
    _max_description = "随机数的最大值（包含）"
    _count_description = "要生成的随机数数量"

    async def execute(
        self,
        min_value: int = 1,
        max_value: int = 100,
        count: Optional[int] = 1
    ) -> ToolResult:
        """
        生成随机数

        Args:
            min_value: 随机数的最小值（包含）
            max_value: 随机数的最大值（包含）
            count: 要生成的随机数数量

        Returns:
            ToolResult: 包含生成的随机数
        """
        try:
            # 参数验证
            if min_value > max_value:
                return ToolResult(
                    success=False,
                    error=f"最小值 {min_value} 不能大于最大值 {max_value}"
                )

            if count <= 0:
                return ToolResult(
                    success=False,
                    error=f"数量 {count} 必须大于0"
                )

            # 生成随机数
            numbers = [random.randint(min_value, max_value) for _ in range(count)]

            # 返回结果
            return ToolResult(
                success=True,
                data={
                    "numbers": numbers,
                    "min": min_value,
                    "max": max_value,
                    "count": count,
                    "sum": sum(numbers),
                    "average": sum(numbers) / count if count > 0 else None
                }
            )

        except Exception as e:
            logger.exception(f"生成随机数出错: {str(e)}")
            return ToolResult(
                success=False,
                error=f"生成随机数出错: {str(e)}"
            )


class TextAnalysisTool(BaseTool):
    """文本分析工具"""

    name = "text_analysis"
    description = "分析文本，计算字符数、单词数等统计信息"

    # 参数描述
    _text_description = "要分析的文本内容"
    _count_words_description = "是否计算单词数"
    _count_sentences_description = "是否计算句子数"

    async def execute(
        self,
        text: str,
        count_words: bool = True,
        count_sentences: bool = True
    ) -> ToolResult:
        """
        分析文本

        Args:
            text: 要分析的文本内容
            count_words: 是否计算单词数
            count_sentences: 是否计算句子数

        Returns:
            ToolResult: 包含文本分析结果
        """
        try:
            # 基本统计
            char_count = len(text)
            char_count_no_spaces = len(text.replace(" ", ""))

            result = {
                "char_count": char_count,
                "char_count_no_spaces": char_count_no_spaces,
            }

            # 计算单词数
            if count_words:
                words = text.split()
                result["word_count"] = len(words)

                # 单词长度分布
                word_lengths = [len(word) for word in words]
                if word_lengths:
                    result["avg_word_length"] = sum(word_lengths) / len(word_lengths)
                    result["min_word_length"] = min(word_lengths) if word_lengths else 0
                    result["max_word_length"] = max(word_lengths) if word_lengths else 0

            # 计算句子数
            if count_sentences:
                # 简单的句子分割（以.!?结尾）
                sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
                result["sentence_count"] = len(sentences)

                # 句子长度分布
                if sentences:
                    sentence_lengths = [len(s) for s in sentences]
                    result["avg_sentence_length"] = sum(sentence_lengths) / len(sentence_lengths)
                    result["min_sentence_length"] = min(sentence_lengths) if sentence_lengths else 0
                    result["max_sentence_length"] = max(sentence_lengths) if sentence_lengths else 0

            # 返回结果
            return ToolResult(
                success=True,
                data=result
            )

        except Exception as e:
            logger.exception(f"分析文本出错: {str(e)}")
            return ToolResult(
                success=False,
                error=f"分析文本出错: {str(e)}"
            )


async def test_random_number_tool() -> None:
    """测试随机数工具"""
    # 创建工具实例
    tool = RandomNumberTool()

    # 注册工具
    ToolRegistry.register(tool)

    # 调用工具
    result = await tool.run(min_value=1, max_value=100, count=5)

    # 打印结果
    print("\n随机数工具测试结果:")
    print(f"成功: {result.success}")
    if result.success:
        print(f"生成的随机数: {result.data['numbers']}")
        print(f"总和: {result.data['sum']}")
        print(f"平均值: {result.data['average']}")
    else:
        print(f"错误: {result.error}")


async def test_text_analysis_tool() -> None:
    """测试文本分析工具"""
    # 创建工具实例
    tool = TextAnalysisTool()

    # 注册工具
    ToolRegistry.register(tool)

    # 测试文本
    text = """
    这是一个示例文本，用于测试文本分析工具。
    它包含多个句子，每个句子有不同的长度和单词数。
    文本分析工具可以计算字符数、单词数和句子数等统计信息。
    """

    # 调用工具
    result = await tool.run(text=text)

    # 打印结果
    print("\n文本分析工具测试结果:")
    print(f"成功: {result.success}")
    if result.success:
        print(f"字符数: {result.data['char_count']}")
        print(f"不含空格的字符数: {result.data['char_count_no_spaces']}")
        print(f"单词数: {result.data['word_count']}")
        print(f"句子数: {result.data['sentence_count']}")
        print(f"平均单词长度: {result.data['avg_word_length']:.2f}")
        print(f"平均句子长度: {result.data['avg_sentence_length']:.2f}")
    else:
        print(f"错误: {result.error}")


async def main() -> None:
    """主函数"""
    print("自定义工具示例")

    # 测试随机数工具
    await test_random_number_tool()

    # 测试文本分析工具
    await test_text_analysis_tool()

    # 打印所有已注册的工具
    tools = ToolRegistry.get_all_tools()
    print(f"\n已注册的工具 ({len(tools)}):")
    for tool in tools:
        print(f"- {tool.name}: {tool.description}")


if __name__ == "__main__":
    asyncio.run(main())