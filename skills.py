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
