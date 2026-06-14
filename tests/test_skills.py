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
