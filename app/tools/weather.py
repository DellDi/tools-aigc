"""
天气查询工具
"""
import logging
from typing import Optional

import httpx

from app.tools.base import BaseTool, ToolRegistry, ToolResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class WeatherTool(BaseTool):
    """天气查询工具"""

    name = "weather"
    description = "查询指定城市的天气信息"

    # 参数描述（用于自动生成参数模式）
    _city_description = "要查询天气的城市名称，例如：北京、上海、广州"
    _country_description = "国家代码，例如：CN（中国）、US（美国）、JP（日本）"
    _units_description = "温度单位，可选值：metric（摄氏度）、imperial（华氏度）、standard（开尔文）"

    async def execute(
        self,
        city: str,
        country: Optional[str] = "CN",
        units: Optional[str] = "metric"
    ) -> ToolResult:
        """
        执行天气查询

        Args:
            city: 城市名称
            country: 国家代码，默认为CN（中国）
            units: 温度单位，默认为metric（摄氏度）

        Returns:
            ToolResult: 查询结果
        """
        # 这里使用OpenWeatherMap API作为示例
        # 实际使用时需要注册并获取API密钥
        # https://openweathermap.org/api
        api_key = settings.OPENWEATHERMAP_API_KEY or ""

        # 构建请求URL
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": f"{city},{country}",
            "units": units,
            "appid": api_key
        }

        try:
            # 发送请求
            async with httpx.AsyncClient() as client:
                # 注意：这里仅作为示例，实际使用时需要替换为真实的API密钥
                # 由于没有真实的API密钥，这里返回模拟数据

                # 模拟数据
                mock_data = {
                    "city": city,
                    "country": country,
                    "temperature": 23.5,
                    "humidity": 65,
                    "weather": "晴天",
                    "wind_speed": 3.2,
                    "units": "摄氏度" if units == "metric" else "华氏度" if units == "imperial" else "开尔文"
                }

                return ToolResult(
                    success=True,
                    data=mock_data
                )

                # 实际代码（需要API密钥）
                # response = await client.get(url, params=params)
                # response.raise_for_status()
                # data = response.json()
                # # 处理响应数据
                # result = {
                #     "city": city,
                #     "country": country,
                #     "temperature": data["main"]["temp"],
                #     "humidity": data["main"]["humidity"],
                #     "weather": data["weather"][0]["description"],
                #     "wind_speed": data["wind"]["speed"],
                #     "units": "摄氏度" if units == "metric" else "华氏度" if units == "imperial" else "开尔文"
                # }
                # return ToolResult(
                #     success=True,
                #     data=result
                # )

        except Exception as e:
            logger.exception(f"天气查询失败: {str(e)}")
            return ToolResult(
                success=False,
                error=f"天气查询失败: {str(e)}"
            )


# 注册工具
ToolRegistry.register(WeatherTool())