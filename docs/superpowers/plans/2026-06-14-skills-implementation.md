# Skills Feature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Agent 新增 prompt 注入型 skill 机制：扫描 `skills/*.md`、按关键词命中把对应指令追加到 system prompt。

**Architecture:** 新建独立模块 `skills.py`，定义 `SkillManager`（与 `MCPClientManager` 对称），在 `Agent.__init__` 启动、`Agent.chat()` 调用。Skill 文件采用 markdown + YAML frontmatter，frontmatter 仅 `name`/`triggers` 两个字段。

**Tech Stack:** Python 3.10+、`pyyaml`（解析 frontmatter）、`pytest`（含 `tmp_path` fixture）。

参考 spec: `docs/superpowers/specs/2026-06-14-skills-design.md`

---

## File Structure

| 文件 | 类型 | 责任 |
|------|------|------|
| `requirements.txt` | 改 | 增加 `pyyaml>=6.0` |
| `skills.py` | 新 | `Skill` dataclass + `SkillManager`：扫描、解析、匹配 |
| `skills/note-taking.md` | 新 | 第一个示例 skill |
| `tests/test_skills.py` | 新 | SkillManager 单测（全部用 `tmp_path`，不依赖仓库根 `skills/`） |
| `tests/test_integration.py` | 改 | 增 1 个用例验证 system prompt 注入 |
| `agent.py` | 改 | `__init__` 实例化 SkillManager；`chat()` 拼接指令 |

---

### Task 1: 添加 pyyaml 依赖

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: 添加依赖行**

把 `requirements.txt` 改为：

```
requests>=2.25.0
mcp>=1.0.0
pytest>=7.0.0
pyyaml>=6.0
```

- [ ] **Step 2: 安装**

Run: `pip install -r requirements.txt`
Expected: 成功安装 `pyyaml`（或提示已满足）。

- [ ] **Step 3: 验证可导入**

Run: `python -c "import yaml; print(yaml.__version__)"`
Expected: 打印版本号（≥6.0）。

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: 添加 pyyaml 依赖以解析 skill frontmatter"
```

---

### Task 2: Skill dataclass + start() 加载单个文件

**Files:**
- Create: `skills.py`
- Create: `tests/test_skills.py`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_skills.py`：

```python
"""SkillManager 单测。所有用例都用 tmp_path 构造临时 skills 目录，不依赖仓库根的 skills/。"""
from skills import SkillManager


def _write_skill(tmp_path, filename, name, triggers_yaml, body):
    """辅助函数：写一个 skill markdown 文件。triggers_yaml 是 YAML 字面量，如 '[foo, bar]'。"""
    content = f"---\nname: {name}\ntriggers: {triggers_yaml}\n---\n{body}\n"
    (tmp_path / filename).write_text(content, encoding="utf-8")


def test_load_valid_skill(tmp_path):
    _write_skill(tmp_path, "alpha.md", "alpha", "[foo, bar]", "规则 A")
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()
    assert len(mgr._skills) == 1
    s = mgr._skills[0]
    assert s.name == "alpha"
    assert s.triggers == ["foo", "bar"]
    assert "规则 A" in s.body
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_skills.py::test_load_valid_skill -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'skills'`

- [ ] **Step 3: 实现最小代码让测试通过**

创建 `skills.py`：

```python
"""Skill 机制：按关键词触发把 skill 正文注入到 system prompt。"""
import os
from dataclasses import dataclass
from typing import List

import yaml


@dataclass
class Skill:
    name: str
    triggers: List[str]
    body: str


class SkillManager:
    """扫描 skills/ 目录，加载 *.md，按用户输入命中触发词激活对应 skill。"""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = skills_dir
        self._skills: List[Skill] = []

    def start(self) -> None:
        """扫描 skills_dir，加载所有 *.md。任何分支都不抛异常。"""
        self._skills = []

        if not os.path.isdir(self.skills_dir):
            print(f"[Skill] skills 目录不存在: {self.skills_dir}")
            return

        for filename in sorted(os.listdir(self.skills_dir)):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(self.skills_dir, filename)
            try:
                skill = self._parse_file(filepath)
                self._skills.append(skill)
                print(f"[Skill] 已加载: {skill.name}")
            except Exception as e:
                print(f"[Skill] 跳过 {filename}: {e}")

    @staticmethod
    def _parse_file(filepath: str) -> Skill:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            raise ValueError("缺少 frontmatter")

        try:
            close_idx = lines.index("---", 1)
        except ValueError:
            raise ValueError("frontmatter 未闭合")

        frontmatter_text = "\n".join(lines[1:close_idx])
        body = "\n".join(lines[close_idx + 1:]).strip("\n")

        meta = yaml.safe_load(frontmatter_text) or {}
        name = meta.get("name")
        triggers = meta.get("triggers")

        if not name or not isinstance(name, str):
            raise ValueError("缺少 name 字段")
        if not triggers or not isinstance(triggers, list):
            raise ValueError("缺少 triggers 字段")

        return Skill(name=name, triggers=triggers, body=body)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_skills.py::test_load_valid_skill -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add skills.py tests/test_skills.py
git commit -m "feat(skills): SkillManager 支持 load 单个 markdown skill"
```

---

### Task 3: get_active_instructions 关键词匹配

**Files:**
- Modify: `skills.py`（新增 `get_active_instructions` 方法）
- Modify: `tests/test_skills.py`（追加测试）

- [ ] **Step 1: 写失败测试**

在 `tests/test_skills.py` 末尾追加：

```python
def test_match_with_trigger(tmp_path):
    _write_skill(tmp_path, "note-taking.md", "note-taking",
                 "[笔记, 记一下, 记录, note]", "笔记规则正文")
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()
    result = mgr.get_active_instructions("帮我记个笔记：买牛奶")
    assert "笔记规则正文" in result


def test_no_match_without_trigger(tmp_path):
    _write_skill(tmp_path, "note-taking.md", "note-taking", "[笔记]", "笔记规则正文")
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()
    assert mgr.get_active_instructions("今天天气怎么样") == ""
```

- [ ] **Step 2: 运行测试确认失败**

Run: `python -m pytest tests/test_skills.py::test_match_with_trigger tests/test_skills.py::test_no_match_without_trigger -v`
Expected: FAIL with `AttributeError: 'SkillManager' object has no attribute 'get_active_instructions'`

- [ ] **Step 3: 实现 get_active_instructions**

在 `skills.py` 的 `SkillManager` 类中追加：

```python
    def get_active_instructions(self, user_input: str) -> str:
        """返回命中 skill 的正文拼接（按 name 字典序），无命中返回空串。"""
        lowered = user_input.lower()
        matched = [
            s for s in self._skills
            if any(t.lower() in lowered for t in s.triggers)
        ]
        matched.sort(key=lambda s: s.name)

        if matched:
            print(f"[Skill] active: {[s.name for s in matched]}")

        return "\n\n".join(s.body for s in matched)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `python -m pytest tests/test_skills.py -v`
Expected: 3 个测试全部 PASS（含 Task 2 的 `test_load_valid_skill`）

- [ ] **Step 5: Commit**

```bash
git add skills.py tests/test_skills.py
git commit -m "feat(skills): get_active_instructions 按子串匹配触发词"
```

---

### Task 4: case-insensitive 匹配 + 多 skill 排序

**Files:**
- Modify: `tests/test_skills.py`（追加 2 个测试，无需改实现——已在 Task 3 用 `.lower()` 实现）

- [ ] **Step 1: 写测试锁定行为**

在 `tests/test_skills.py` 末尾追加：

```python
def test_match_case_insensitive(tmp_path):
    _write_skill(tmp_path, "note.md", "note", "[note]", "英文规则正文")
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()
    assert "英文规则正文" in mgr.get_active_instructions("Take a NOTE please")


def test_multiple_matches_sorted_by_name(tmp_path):
    _write_skill(tmp_path, "zeta.md", "zeta", "[common]", "Z 正文")
    _write_skill(tmp_path, "alpha.md", "alpha", "[common]", "A 正文")
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()
    result = mgr.get_active_instructions("common trigger")
    # alpha 字典序在 zeta 之前 → A 正文必须先出现
    assert result.index("A 正文") < result.index("Z 正文")
```

- [ ] **Step 2: 运行测试确认通过（行为已在前置 Task 实现完）**

Run: `python -m pytest tests/test_skills.py -v`
Expected: 5 个测试全部 PASS。

如果失败：检查 `get_active_instructions` 是否对 user_input 和 triggers 都做了 `.lower()`；检查 matched 是否做了 `sort(key=lambda s: s.name)`。

- [ ] **Step 3: Commit**

```bash
git add tests/test_skills.py
git commit -m "test(skills): 锁定 case-insensitive 与多 skill 字典序拼接"
```

---

### Task 5: 错误处理 —— 跳过坏文件 / 空 / 不存在的目录

**Files:**
- Modify: `tests/test_skills.py`（追加 3 个测试，实现已在 Task 2 完整覆盖）

- [ ] **Step 1: 写测试**

在 `tests/test_skills.py` 末尾追加：

```python
def test_skip_malformed_files(tmp_path):
    # 1) 缺 frontmatter
    (tmp_path / "no_frontmatter.md").write_text("纯文本没有 frontmatter", encoding="utf-8")
    # 2) frontmatter 未闭合
    (tmp_path / "unclosed.md").write_text("---\nname: x\nbody", encoding="utf-8")
    # 3) YAML 语法错
    (tmp_path / "bad_yaml.md").write_text("---\nname: x\ntriggers: [unclosed\n---\nbody", encoding="utf-8")
    # 4) 缺 name 字段
    (tmp_path / "no_name.md").write_text("---\ntriggers: [foo]\n---\nbody", encoding="utf-8")
    # 5) 缺 triggers 字段
    (tmp_path / "no_triggers.md").write_text("---\nname: x\n---\nbody", encoding="utf-8")
    # 合法文件应正常加载
    _write_skill(tmp_path, "good.md", "good", "[foo]", "good body")

    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()  # 不抛

    assert len(mgr._skills) == 1
    assert mgr._skills[0].name == "good"


def test_empty_skills_dir(tmp_path):
    mgr = SkillManager(skills_dir=str(tmp_path))
    mgr.start()  # 不抛
    assert mgr._skills == []
    assert mgr.get_active_instructions("anything") == ""


def test_missing_skills_dir(tmp_path):
    missing = str(tmp_path / "does_not_exist")
    mgr = SkillManager(skills_dir=missing)
    mgr.start()  # 不抛
    assert mgr._skills == []
    assert mgr.get_active_instructions("anything") == ""
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_skills.py -v`
Expected: 8 个测试全部 PASS。

如果失败，对照 `skills.py` 的 `_parse_file`：必须检查 `lines[0].strip() != "---"`、`lines.index("---", 1)` 可能 `ValueError`、YAML 解析可能抛 `yaml.YAMLError`、`name`/`triggers` 必须存在且类型正确。`start()` 的 for 循环必须用 `try/except` 包住 `_parse_file`。

- [ ] **Step 3: Commit**

```bash
git add tests/test_skills.py
git commit -m "test(skills): 覆盖坏文件跳过与空/缺失目录场景"
```

---

### Task 6: 创建示例 skill 文件 skills/note-taking.md

**Files:**
- Create: `skills/note-taking.md`

- [ ] **Step 1: 创建目录与文件**

创建 `skills/note-taking.md`：

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

- [ ] **Step 2: 验证可被 SkillManager 加载**

Run: `python -c "from skills import SkillManager; m = SkillManager(); m.start(); print('skills:', [s.name for s in m._skills]); print('match:', bool(m.get_active_instructions('记一下')))"`

Expected: 输出包含 `skills: ['note-taking']` 和 `match: True`，并打印 `[Skill] 已加载: note-taking` 和 `[Skill] active: ['note-taking']`。

- [ ] **Step 3: Commit**

```bash
git add skills/note-taking.md
git commit -m "feat(skills): 添加 note-taking 示例 skill"
```

---

### Task 7: Agent 集成 —— 启动加载 + chat() 拼接

**Files:**
- Modify: `agent.py`

- [ ] **Step 1: 修改 agent.py**

在 `agent.py` 顶部 import 段加入（与现有 `from mcp_client import MCPClientManager` 同段）：

```python
from skills import SkillManager
```

修改 `Agent.__init__`，在 `self.tools_schema = get_tools_schema()` 之后、`self.mcp_manager: Optional[MCPClientManager] = None` 之前插入：

```python
        # 加载 skills
        self.skill_manager = SkillManager()
        self.skill_manager.start()
```

修改 `Agent.chat()` 的开头，把当前的：

```python
        messages = [
            {"role": "system", "content": "你是一个有帮助的助手，可以使用工具帮助用户完成任务。"},
            {"role": "user", "content": user_input}
        ]
```

替换为：

```python
        system_prompt = "你是一个有帮助的助手，可以使用工具帮助用户完成任务。"

        active = self.skill_manager.get_active_instructions(user_input)
        if active:
            system_prompt += "\n\n" + active

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
```

`chat()` 后续循环逻辑保持不变。

- [ ] **Step 2: 回归现有测试**

Run: `python -m pytest tests/ -v`
Expected: 所有现有测试（含 `test_integration.py::test_full_workflow`、`test_agent.py`、`test_config.py`、`test_logger.py`、`test_tools.py`、`test_missing_tool.py`）+ 8 个新 skills 测试全部 PASS。

注意：现有集成测试会触发 SkillManager 扫描仓库根真实的 `skills/note-taking.md`，但用户输入是 `"读取文件 xxx"`，不会命中 `note-taking` 的触发词，所以 system prompt 不变、测试仍应通过。如果某测试用例的输入恰好包含 `笔记`/`记一下`/`记录`/`note` 子串导致 system prompt 变化而失败，需用 `unittest.mock.patch('agent.SkillManager')` 或给该测试构造空 skills dir——优先排查测试输入。

- [ ] **Step 3: 手动冒烟**

Run: `python -c "from config import load_config; from agent import Agent; a = Agent(load_config()); print(repr(a.skill_manager.get_active_instructions('记一下买牛奶')))"`
Expected: 打印 note-taking 正文（含"当用户要求记录信息时..."）。

- [ ] **Step 4: Commit**

```bash
git add agent.py
git commit -m "feat(agent): 启动加载 SkillManager，chat() 按命中注入 system prompt"
```

---

### Task 8: 集成测试 —— 验证 system prompt 注入

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: 写测试**

在 `tests/test_integration.py` 末尾追加：

```python
def test_skill_injected_into_system_prompt():
    """触发词命中时，skill 正文应出现在发给 API 的 system prompt 中。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # 构造一个包含 note-taking skill 的临时目录
        skills_dir = os.path.join(tmpdir, "skills")
        os.makedirs(skills_dir)
        with open(os.path.join(skills_dir, "note-taking.md"), "w", encoding="utf-8") as f:
            f.write(
                "---\nname: note-taking\ntriggers: [笔记]\n---\n"
                "记笔记专属规则 XYZ\n"
            )

        with patch("agent.SkillManager") as MockManager:
            # 让 Agent 内部用的是这个 stub，指向我们准备的临时 skills
            from skills import SkillManager as Real
            instance = MockManager.return_value
            instance.start.return_value = None
            instance.get_active_instructions.return_value = "记笔记专属规则 XYZ"

            with patch("agent.requests.post") as mock_post:
                mock_post.return_value.json.return_value = {
                    "choices": [{"message": {"role": "assistant", "content": "ok"}}]
                }
                mock_post.return_value.raise_for_status = Mock()

                config = Config(
                    api_key="test-key",
                    log_dir=os.path.join(tmpdir, "logs"),
                )
                agent = Agent(config)
                agent.chat("帮我记个笔记")

                # 第一次 POST 的 payload 中，messages[0] 应是 system，且包含 skill 正文
                first_payload = mock_post.call_args_list[0].kwargs["json"]
                assert first_payload["messages"][0]["role"] == "system"
                assert "记笔记专属规则 XYZ" in first_payload["messages"][0]["content"]
```

- [ ] **Step 2: 运行测试确认通过**

Run: `python -m pytest tests/test_integration.py::test_skill_injected_into_system_prompt -v`
Expected: PASS。

- [ ] **Step 3: 全量回归**

Run: `python -m pytest tests/ -v`
Expected: 所有测试 PASS。

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration.py
git commit -m "test(agent): 验证 skill 正文被注入到 system prompt"
```

---

## Self-Review 结果

**Spec 覆盖检查**：
- §2 skill 文件格式 → Task 6 落地示例，Task 2 单测验证解析
- §2 SkillManager API（`start` / `get_active_instructions`）→ Task 2/3
- §2 匹配规则（子串、case-insensitive、字典序）→ Task 3/4
- §2 frontmatter 解析（手动 split + `yaml.safe_load`）→ Task 2 `_parse_file`
- §3 Agent 集成（`__init__` 实例化 + `chat()` 拼接）→ Task 7
- §3 错误处理表全部场景 → Task 5（含缺 frontmatter / 未闭合 / YAML 错 / 缺 name / 缺 triggers / 空 dir / 缺失 dir）
- §3 调试可见性（`[Skill]` 打印）→ Task 2/3 实现已含 `print`
- §4 测试计划 8 个单测 → Task 2-5 一一对应
- §4 可选集成测试 → Task 8

**Placeholder 扫描**：无 TBD/TODO/抽象描述，所有代码块均为完整可粘贴内容。

**类型一致性**：`Skill` 字段（`name`/`triggers`/`body`）、`SkillManager.skills_dir`、`_skills`、`get_active_instructions(user_input) -> str` 在所有任务中命名一致。

**YAML 错误测试注意**：Task 5 的 `bad_yaml.md` 内容 `triggers: [unclosed` 会让 `yaml.safe_load` 抛 `yaml.scanner.ScannerError`，被 `start()` 的 `except Exception` 捕获并跳过——符合预期。
