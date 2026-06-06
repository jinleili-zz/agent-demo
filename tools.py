import inspect
import os
import json
from typing import Callable, Dict, List, Any
from functools import wraps

import requests

# 工具注册表
_registry: Dict[str, Callable] = {}
_schemas: List[Dict] = []

def register_tool(description: str = ""):
    """工具注册装饰器
    
    Args:
        description: 工具描述
        
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        tool_name = func.__name__
        _registry[tool_name] = func
        
        # 生成 OpenAI 格式的工具 schema
        sig = inspect.signature(func)
        properties = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            
            properties[param_name] = {"type": param_type}
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
        _schemas.append(schema)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator

def get_tools_schema() -> List[Dict]:
    """获取所有已注册工具的 schema"""
    return _schemas.copy()

def execute_tool(name: str, arguments: Dict[str, Any]) -> Any:
    """执行指定工具
    
    Args:
        name: 工具名称
        arguments: 工具参数
        
    Returns:
        工具执行结果
        
    Raises:
        ValueError: 工具不存在
    """
    if name not in _registry:
        raise ValueError(f"工具不存在: {name}")
    
    func = _registry[name]
    return func(**arguments)

def _validate_path(path: str) -> str:
    """验证文件路径，确保在工作目录内

    Args:
        path: 文件路径

    Returns:
        规范化后的绝对路径

    Raises:
        ValueError: 路径不在工作目录内
    """
    workspace = os.path.realpath(os.getcwd())
    normalized_path = os.path.realpath(os.path.expanduser(path))

    try:
        common = os.path.commonpath([workspace, normalized_path])
    except ValueError:
        raise ValueError(f"路径不在工作目录内: {path}")

    if common != workspace:
        raise ValueError(f"路径不在工作目录内: {path}")

    return normalized_path

@register_tool(description="读取文件内容")
def read_file(path: str) -> str:
    """读取文件内容
    
    Args:
        path: 文件路径
        
    Returns:
        文件内容
        
    Raises:
        ValueError: 路径越界
        FileNotFoundError: 文件不存在
    """
    abs_path = _validate_path(path)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"文件不存在: {path}")

    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        raise ValueError(f"无法读取文件（非文本文件）: {path}")


# 常见中文城市名 → 英文名映射（Open-Meteo Geocoding 不识别部分中文名）
_CITY_ALIASES = {
    "纽约": "New York",
    "伦敦": "London",
    "旧金山": "San Francisco",
    "洛杉矶": "Los Angeles",
    "华盛顿": "Washington",
    "悉尼": "Sydney",
    "墨尔本": "Melbourne",
    "多伦多": "Toronto",
    "温哥华": "Vancouver",
    "柏林": "Berlin",
    "罗马": "Rome",
    "莫斯科": "Moscow",
    "首尔": "Seoul",
    "曼谷": "Bangkok",
    "新加坡": "Singapore",
}


def _geocode(city: str, language: str, country: str = "") -> list:
    """调用 Open-Meteo Geocoding API，返回按人口降序排序的结果列表"""
    geo_params = {"name": city, "count": 10, "language": language}
    if country:
        geo_params["country"] = country

    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params=geo_params,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results") or []
    return sorted(results, key=lambda r: r.get("population") or 0, reverse=True)


@register_tool(description="查询指定城市的当前天气，返回温度、湿度、风速等信息")
def get_weather(city: str, country: str = "") -> str:
    """查询指定城市的当前天气

    Args:
        city: 城市名称（支持中英文，如 "北京"、"Tokyo"、"New York"）
        country: 国家名称或代码（可选，用于消歧义，如 "US"、"CN"、"日本"）

    Returns:
        天气信息字符串
    """
    try:
        # 1. Geocoding: 城市名 → 经纬度
        # 对于已知别名，直接使用英文名搜索
        search_city = _CITY_ALIASES.get(city, city)

        # 同时搜索中英文，合并去重后按人口排序，确保中英文城市名都能匹配
        zh_results = _geocode(search_city, "zh", country)
        en_results = _geocode(search_city, "en", country)

        # 按 ID 去重，合并结果
        seen_ids = set()
        all_results = []
        for r in zh_results + en_results:
            rid = r.get("id")
            if rid not in seen_ids:
                seen_ids.add(rid)
                all_results.append(r)

        # 按人口降序排序
        all_results.sort(key=lambda r: r.get("population") or 0, reverse=True)

        if not all_results:
            return f"未找到城市: {city}"

        location = all_results[0]
        latitude = location["latitude"]
        longitude = location["longitude"]
        location_name = location.get("name", city)
        country_name = location.get("country", "")
        admin1 = location.get("admin1", "")  # 省/州

        # 如果有多个候选，列出供参考
        if len(all_results) > 1:
            candidates = [
                f"{r.get('name', '')}, {r.get('admin1', '')}, {r.get('country', '')}"
                for r in all_results[1:4]
            ]
            candidates_hint = f"（其他候选: {'; '.join(candidates)}）"
        else:
            candidates_hint = ""

        # 2. 查询天气
        weather_resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "timezone": "auto",
            },
            timeout=10,
        )
        weather_resp.raise_for_status()
        weather_data = weather_resp.json()

        current = weather_data.get("current", {})
        temp = current.get("temperature_2m", "N/A")
        humidity = current.get("relative_humidity_2m", "N/A")
        wind_speed = current.get("wind_speed_10m", "N/A")
        weather_code = current.get("weather_code", 0)

        # WMO 天气代码 → 中文描述
        weather_desc_map = {
            0: "晴", 1: "大部晴", 2: "多云", 3: "阴",
            45: "雾", 48: "雾凇", 51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
            61: "小雨", 63: "中雨", 65: "大雨", 71: "小雪", 73: "中雪", 75: "大雪",
            80: "阵雨", 81: "中阵雨", 82: "大阵雨", 95: "雷阵雨", 96: "冰雹雷阵雨",
        }
        weather_desc = weather_desc_map.get(weather_code, f"未知({weather_code})")

        location_label = f"{location_name}, {admin1}, {country_name}" if admin1 else f"{location_name}, {country_name}"

        return (
            f"{location_label} {candidates_hint}\n"
            f"天气: {weather_desc}\n"
            f"温度: {temp}°C\n"
            f"湿度: {humidity}%\n"
            f"风速: {wind_speed} km/h"
        )
    except Exception as e:
        return f"查询天气失败: {e}"


@register_tool(description="写入文件内容")
def write_file(path: str, content: str) -> str:
    """写入文件内容
    
    Args:
        path: 文件路径
        content: 文件内容
        
    Returns:
        操作结果
        
    Raises:
        ValueError: 路径越界
    """
    abs_path = _validate_path(path)
    
    # 确保目录存在
    os.makedirs(os.path.dirname(abs_path) or '.', exist_ok=True)
    
    with open(abs_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return f"文件已写入: {path}"
