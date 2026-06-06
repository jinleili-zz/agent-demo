import json
import os
from dataclasses import dataclass, field
from typing import Dict, Any


@dataclass
class Config:
    """配置数据类"""
    api_key: str
    base_url: str = "https://api.deepseek.com/v1"
    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 4096
    log_dir: str = "logs"
    mcp_servers: Dict[str, Any] = field(default_factory=dict)


def load_config(config_path: str = "config.json") -> Config:
    """加载配置文件
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        Config 对象
        
    Raises:
        FileNotFoundError: 配置文件不存在
        ValueError: api_key 为空
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    api_key = data.get('api_key', '').strip()
    if not api_key:
        raise ValueError("api_key 是必填项")
    
    return Config(
        api_key=api_key,
        base_url=data.get('base_url', Config.base_url),
        model=data.get('model', Config.model),
        temperature=data.get('temperature', Config.temperature),
        max_tokens=data.get('max_tokens', Config.max_tokens),
        log_dir=data.get('log_dir', Config.log_dir),
        mcp_servers=data.get('mcp_servers', {})
    )
