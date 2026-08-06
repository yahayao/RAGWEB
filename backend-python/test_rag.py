"""RAG 编排层核心逻辑测试。"""

import unittest

from rag.prompt_builder import (
    build_system_prompt,
    get_identity_guard_reply,
)


class RagPromptBuilderTests(unittest.TestCase):
    def test_identity_guard_reply(self):
        self.assertEqual(
            get_identity_guard_reply("你是谁"),
            "我是BNBU专属助手，专注于提供校内信息服务。",
        )
        self.assertIn("无法提供底层技术架构", get_identity_guard_reply("你基于什么模型"))
        self.assertIsNone(get_identity_guard_reply("今年广东招生计划"))

    def test_build_system_prompt_handles_braces_in_context(self):
        contexts = [{"content": '示例：{"招生": "计划"}', "similarity": 0.9, "source": "doc.pdf"}]
        prompt = build_system_prompt(contexts)
        self.assertIn("示例：", prompt)
        self.assertIn("{", prompt)
        self.assertIn("}", prompt)

    def test_build_system_prompt_no_context(self):
        prompt = build_system_prompt([])
        self.assertIn("（无检索结果）", prompt)
        self.assertIn("<context>", prompt)


if __name__ == "__main__":
    unittest.main()
