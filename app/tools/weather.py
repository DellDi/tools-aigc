"""
天气查询工具 - 使用 OpenWeatherMap One Call API 3.0
"""
import logging
from typing import Optional, Dict, Any

import httpx

from app.tools.base import BaseTool, ToolRegistry, ToolResult
from app.core.config import settings

logger = logging.getLogger("uvicorn")

class WeatherTool(BaseTool):
    """天气查询工具 - 使用 OpenWeatherMap One Call API 3.0"""

    name = "weather"
    description = "查询指定城市的天气信息，包括当前天气、小时预报和每日预报"

    # 参数描述（用于自动生成参数模式）
    _city_description = "要查询天气的城市名称，例如：北京、上海、广州"
    _country_description = "国家代码，例如：CN（中国）、US（美国）、JP（日本）"
    _units_description = "温度单位，可选值：metric（摄氏度）、imperial（华氏度）、standard（开尔文）"
    _exclude_description = "排除的数据部分，可选值：current,minutely,hourly,daily,alerts，用逗号分隔"

    async def execute(
        self,
        city: str,
        country: Optional[str] = "CN",
        units: Optional[str] = "metric",
        exclude: Optional[str] = ""
    ) -> ToolResult:
        """
        执行天气查询

        Args:
            city: 城市名称
            country: 国家代码，默认为CN（中国）
            units: 温度单位，默认为metric（摄氏度）
            exclude: 排除的数据部分，可选值：current,minutely,hourly,daily,alerts，用逗号分隔

        Returns:
            ToolResult: 查询结果
        """
        # 获取 API 密钥
        api_key = settings.OPENWEATHERMAP_API_KEY or ""
        if not api_key:
            return ToolResult(
                success=False,
                error="未配置 OpenWeatherMap API 密钥"
            )
        logger.info(f"使用 API 密钥: {api_key[:5]}...")
        try:
            # 步骤 1: 使用 Geocoding API 获取城市的经纬度
            geo_url = "https://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                "q": f"{city},{country}",
                "limit": 1,
                "appid": api_key
            }

            async with httpx.AsyncClient() as client:
                geo_response = await client.get(geo_url, params=geo_params)
                geo_response.raise_for_status()
                geo_data = geo_response.json()

                if not geo_data:
                    return ToolResult(
                        success=False,
                        error=f"找不到城市: {city}, {country}"
                    )

                # 获取第一个匹配结果的经纬度
                lat = geo_data[0]["lat"]
                lon = geo_data[0]["lon"]
                location_name = geo_data[0].get("local_names", {}).get("zh", geo_data[0]["name"])

                # 步骤 2: 使用 One Call API 3.0 获取天气数据
                weather_url = "https://api.openweathermap.org/data/3.0/onecall"
                weather_params = {
                    "lat": lat,
                    "lon": lon,
                    "units": units,
                    "appid": api_key
                }

                # 添加可选的 exclude 参数
                if exclude:
                    weather_params["exclude"] = exclude

                weather_response = await client.get(weather_url, params=weather_params)
                weather_response.raise_for_status()
                weather_data = weather_response.json()

                # 处理响应数据
                result = self._process_weather_data(weather_data, city, country, units, location_name)
                return ToolResult(
                    success=True,
                    data=result
                )

        except Exception as e:
            logger.exception(f"天气查询失败: {str(e)}")
            return ToolResult(
                success=False,
                error=f"天气查询失败: {str(e)}"
            )

    def _process_weather_data(self, data: Dict[str, Any], city: str, country: str, units: str, location_name: str) -> Dict[str, Any]:
        """
        处理天气 API 返回的数据

        Args:
            data: One Call API 返回的原始数据
            city: 查询的城市名称
            country: 国家代码
            units: 温度单位
            location_name: 地理编码返回的位置名称

        Returns:
            Dict[str, Any]: 处理后的天气数据
        """
        # 单位显示文本
        units_text = "摄氏度" if units == "metric" else "华氏度" if units == "imperial" else "开尔文"

        # 基本信息
        result = {
            "city": city,
            "location_name": location_name,
            "country": country,
            "timezone": data["timezone"],
            "units": units_text
        }

        # 当前天气
        if "current" in data:
            current = data["current"]
            result["current"] = {
                "temperature": current["temp"],
                "feels_like": current["feels_like"],
                "humidity": current["humidity"],
                "pressure": current["pressure"],
                "uvi": current["uvi"],
                "clouds": current["clouds"],
                "visibility": current["visibility"],
                "wind_speed": current["wind_speed"],
                "wind_deg": current["wind_deg"],
                "weather": {
                    "main": current["weather"][0]["main"],
                    "description": current["weather"][0]["description"],
                    "icon": current["weather"][0]["icon"]
                }
            }

        # 每小时预报（仅包含前 6 小时）
        if "hourly" in data:
            result["hourly"] = []
            for i, hour in enumerate(data["hourly"]):
                if i >= 6:  # 只取前 6 小时数据
                    break
                result["hourly"].append({
                    "dt": hour["dt"],
                    "temperature": hour["temp"],
                    "weather": hour["weather"][0]["description"],
                    "pop": hour.get("pop", 0) * 100  # 降水概率转为百分比
                })

        # 每日预报（仅包含前 3 天）
        if "daily" in data:
            result["daily"] = []
            for i, day in enumerate(data["daily"]):
                if i >= 3:  # 只取前 3 天数据
                    break
                result["daily"].append({
                    "dt": day["dt"],
                    "summary": day.get("summary", ""),
                    "temperature": {
                        "day": day["temp"]["day"],
                        "min": day["temp"]["min"],
                        "max": day["temp"]["max"]
                    },
                    "weather": day["weather"][0]["description"],
                    "pop": day.get("pop", 0) * 100  # 降水概率转为百分比
                })

        # 天气预警
        if "alerts" in data and data["alerts"]:
            result["alerts"] = []
            for alert in data["alerts"]:
                result["alerts"].append({
                    "event": alert["event"],
                    "description": alert["description"],
                    "start": alert["start"],
                    "end": alert["end"]
                })

        return result


# 注册工具
ToolRegistry.register(WeatherTool())