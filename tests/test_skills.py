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
