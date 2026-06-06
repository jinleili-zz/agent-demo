import sys
from config import load_config
from agent import Agent


def main():
    """主函数"""
    try:
        config = load_config()
        agent = Agent(config)
        
        print("=" * 50)
        print("Simple Agent - 基于 DeepSeek")
        print("输入 'exit' 或 'quit' 退出")
        print("=" * 50)
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ('exit', 'quit'):
                    print("再见！")
                    break
                
                print("\nAgent: ", end="", flush=True)
                response = agent.chat(user_input)
                print(response)
                
            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                print(f"\n错误: {e}")
    
    except FileNotFoundError:
        print("错误: 配置文件 config.json 不存在")
        print("请创建 config.json，格式如下:")
        print('  {"api_key": "your-api-key"}')
        sys.exit(1)
    except ValueError as e:
        print(f"配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
