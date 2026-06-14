# Skills Feature Design

**Date:** 2026-06-14
**Status:** Approved (pending implementation)

## 目的

为现有 Agent 增加 "skill" 机制。Skill 是一段**给模型读的指令文本**，在用户输入命中触发词时被注入到 system prompt，从而改变 Agent 在该任务下的行为方式。这与现有 "tool"（给模型调用的函数）形成清晰的互补：

- **Tool** = 能力（agent 能做什么）
- **Skill** = 规范（agent 在某类任务下应该怎么做）

本特性的首个内置 skill 是 `note-taking`，用于演示机制完整闭环。

## 范围

- 实现一个独立模块 `SkillManager`，负责扫描、加载、按用户输入匹配 skill。
- 在 `Agent.chat()` 构造 messages 时，把命中 skill 的正文追加到 system prompt。
- 提供一个示例 skill `note-taking`。
- 配套单测覆盖 `SkillManager`。

**不在范围内**：热重载、模型自选 skill（meta-tool）、skill 之间的依赖关系、skill 国际化。

## 文件布局

```
agent.py              [改] __init__ 实例化 SkillManager；chat() 拼接 skill 指令
skills.py             [新] SkillManager 类
skills/note-taking.md [新] 第一个示例 skill
tests/test_skills.py  [新] SkillManager 单测
requirements.txt      [改] 增加 pyyaml>=6.0
```

`skills/` 目录与 `tools.py` / `mcp_client.py` 平级，放在仓库根。运行期不需要改 skill，启动时**一次性扫描加载**。

## skill 文件格式

Markdown + YAML frontmatter，存放于 `skills/*.md`：

```markdown
---
name: note-taking
triggers: [笔记, 记一下, 记录, note]
---

当用户要求记录信息时：
1. 文件统一写到 notes/YYYY-MM-DD.md（YYYY-MM-DD 为当天日期）
2. 追加而非覆盖
3. 每条格式：`- HH:MM 内容`
4. 写完后简短确认，不要复述全部内容
```

**frontmatter 字段**（均为必填）：

| 字段 | 类型 | 用途 |
|------|------|------|
| `name` | str | skill 唯一标识；同时是多命中时排序的依据 |
| `triggers` | list[str] | 触发关键词；任一命中即激活 |

frontmatter 之后的全部内容就是要注入给模型的指令文本（纯 markdown）。

## SkillManager API

`skills.py`：

```python
@dataclass
class Skill:
    name: str
    triggers: list[str]
    body: str

class SkillManager:
    def __init__(self, skills_dir: str = "skills"): ...
    def start(self) -> None:
        """扫描 skills_dir，加载所有 *.md。任何分支都不抛异常。"""
    def get_active_instructions(self, user_input: str) -> str:
        """返回命中 skill 的正文拼接，无命中返回 ""。"""
```

**匹配规则**：

- 子串匹配，case-insensitive（英文 trigger 如 `note` 也能命中 `NOTE` / `Take a note`）。
- triggers 列表里任意一个命中即激活该 skill。
- 多个 skill 同时命中 → 按 `name` 字典序拼接，确保输出稳定可测试。

**frontmatter 解析**：手动按 `---` 分隔——读文件首行需为 `---`，找到下一处独占一行的 `---`，中间用 `yaml.safe_load`，其后内容作为 `body`。不引入第三方 markdown 库。

## Agent 集成

**`Agent.__init__`** 在 logger/tools 之后、MCP 之前实例化：

```python
self.skill_manager = SkillManager()
self.skill_manager.start()
```

**`Agent.chat()`** 仅修改 messages 构造段，其余循环逻辑保持不变：

```python
def chat(self, user_input: str) -> str:
    system_prompt = "你是一个有帮助的助手，可以使用工具帮助用户完成任务。"

    active = self.skill_manager.get_active_instructions(user_input)
    if active:
        system_prompt += "\n\n" + active

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input}
    ]
    # ... 后续 max_rounds 循环逻辑不变
```

每个 `chat()` 调用独立构造 messages（与现有设计一致），所以 skill 只在命中那一轮生效，不会跨轮泄漏。

**注入后的 system prompt 示例**（用户输入 "帮我记个笔记：买牛奶"）：

```
你是一个有帮助的助手，可以使用工具帮助用户完成任务。

当用户要求记录信息时：
1. 文件统一写到 notes/YYYY-MM-DD.md（YYYY-MM-DD 为当天日期）
2. 追加而非覆盖
3. 每条格式：`- HH:MM 内容`
4. 写完后简短确认，不要复述全部内容
```

## 错误处理

保守策略：绝不让 skill 模块拖垮 Agent 启动或运行。

| 情况 | 行为 |
|------|------|
| `skills/` 目录不存在 | 打印 warning，`_skills=[]` |
| 目录存在但为空 | 同上 |
| 单个 `.md` 缺 frontmatter / YAML 格式错 / 缺 `name` 或 `triggers` | 跳过该文件，打印 warning，其他文件继续加载 |
| `start()` 整体不抛异常 | ✓ |
| `get_active_instructions()` 永远返回 str | ✓ |

**调试可见性**：命中时打印 `[Skill] active: ['note-taking']`，与现有 `[MCP]` / `[Agent]` 前缀打印风格一致。

## 测试计划

**`tests/test_skills.py`**（单测 SkillManager，不起 Agent）：

| 测试 | 验证 |
|------|------|
| `test_load_valid_skill` | 合法 `.md` → `_skills` 长度 1，name/triggers/body 都正确解析 |
| `test_match_with_trigger` | `user_input="帮我记个笔记：买牛奶"` → 返回 note-taking 正文 |
| `test_no_match_without_trigger` | `user_input="今天天气怎么样"` → 返回 `""` |
| `test_match_case_insensitive` | triggers 含 `note`，`user_input="Take a NOTE"` → 命中 |
| `test_multiple_matches_sorted_by_name` | 临时建两个 skill 文件，输入同时命中两者 → 按 name 字典序拼接 |
| `test_skip_malformed_file` | 缺 frontmatter / YAML 错 / 缺必填字段的 `.md` → 跳过且不抛异常 |
| `test_empty_skills_dir` | 用 tmp 空目录构造 → `_skills=[]`，`start()` 不抛 |
| `test_missing_skills_dir` | 用不存在的目录构造 → 同上 |

技巧：用 pytest 的 `tmp_path` fixture 给每个测试建独立临时 `skills/` 目录，**不依赖**仓库根真实的 `skills/note-taking.md`——否则新增 skill 文件时单测会变红。

**`tests/test_integration.py` 增量（可选）**：mock API，发送带触发词的输入，断言传给 API 的 `messages[0]["content"]` 包含 note-taking 正文。验证 `Agent.chat()` 的拼接逻辑。

**不测的部分**：真实 DeepSeek API 调用（保持现有测试一贯不引入网络依赖的风格）、模型是否真的按 skill 行为写文件（行为正确性归模型本身，skill 只保证指令被正确送达）。
