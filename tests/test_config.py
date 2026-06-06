import json
import pytest
import tempfile
import os
from config import load_config, Config


def test_load_config_success():
    """测试成功加载配置"""
    config_data = {
        "api_key": "test-key-123",
        "base_url": "https://test.com",
        "model": "test-model",
        "temperature": 0.5,
        "max_tokens": 2048,
        "log_dir": "test_logs"
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config_path = f.name
    
    try:
        config = load_config(config_path)
        assert config.api_key == "test-key-123"
        assert config.base_url == "https://test.com"
        assert config.model == "test-model"
        assert config.temperature == 0.5
        assert config.max_tokens == 2048
        assert config.log_dir == "test_logs"
    finally:
        os.unlink(config_path)


def test_load_config_missing_api_key():
    """测试缺失 api_key 时抛出异常"""
    config_data = {"model": "test-model"}
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        f.flush()
        config_path = f.name
    
    try:
        with pytest.raises(ValueError, match="api_key 是必填项"):
            load_config(config_path)
    finally:
        os.unlink(config_path)
