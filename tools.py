import os
import json
from typing import Callable, Dict, List, Any
from functools import wraps

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
        import inspect
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
    # Get the workspace root (current working directory)
    workspace = os.path.abspath(os.getcwd())
    
    # Normalize the path
    normalized_path = os.path.abspath(os.path.expanduser(path))
    
    # Check if the path is within the workspace
    if not normalized_path.startswith(workspace):
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
    
    with open(abs_path, 'r', encoding='utf-8') as f:
        return f.read()

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
