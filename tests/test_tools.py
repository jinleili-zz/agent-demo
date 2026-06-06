import pytest
import tempfile
import os
from tools import register_tool, get_tools_schema, execute_tool

def test_register_tool_decorator():
    """测试工具注册装饰器"""
    initial_count = len(get_tools_schema())
    
    @register_tool(description="测试工具")
    def test_tool(name: str) -> str:
        return f"Hello {name}"
    
    schema = get_tools_schema()
    assert len(schema) == initial_count + 1
    assert schema[-1]["function"]["name"] == "test_tool"
    assert schema[-1]["function"]["description"] == "测试工具"

def test_execute_tool_read_file():
    """测试读取文件工具"""
    # 创建临时文件（在当前工作目录内）
    temp_path = os.path.join(os.getcwd(), "test_read_temp.txt")
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write("Hello World")
    
    try:
        result = execute_tool("read_file", {"path": temp_path})
        assert result == "Hello World"
    finally:
        os.unlink(temp_path)

def test_execute_tool_write_file():
    """测试写入文件工具"""
    file_path = os.path.join(os.getcwd(), "test_write_temp.txt")
    result = execute_tool("write_file", {"path": file_path, "content": "Test Content"})
    assert "文件已写入" in result
    
    # 验证写入内容
    with open(file_path, 'r', encoding='utf-8') as f:
        assert f.read() == "Test Content"
    
    # 清理
    os.unlink(file_path)

def test_execute_tool_path_traversal():
    """测试路径越界检测"""
    with pytest.raises(ValueError, match="路径不在工作目录内"):
        execute_tool("read_file", {"path": "/etc/passwd"})
