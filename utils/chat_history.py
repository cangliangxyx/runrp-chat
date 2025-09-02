# utils/chat_history.py

import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


class ChatHistory:
    """
    管理聊天历史

    功能：
    - 保存最近 N 条对话
    - 支持格式化输出用于拼接系统 prompt
    - 自动持久化到文件
    - 提取故事摘要
    """

    HISTORY_FILE = Path(__file__).resolve().parent.parent / "log/chat_history.json"

    def __init__(self, max_entries: int = 50):
        """
        初始化聊天历史管理器

        Args:
            max_entries: 最大保存历史条数，超过会自动删除最早记录
        """
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []
        self.load_history()

    def add_entry(self, user: str, assistant: str) -> None:
        """
        添加一条对话记录

        Args:
            user: 用户输入文本
            assistant: 模型回复文本
        """
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user.strip(),
            "assistant": assistant.strip()
        }
        self.entries.append(entry)

        # 超出最大条数时，保留最新 max_entries 条
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        self.save_history()

    def format_history(self, max_entries: Optional[int] = None) -> str:
        """
        格式化历史记录，便于拼接到系统 prompt

        Args:
            max_entries: 可选，限制输出的历史记录条数
        Returns:
            str: 格式化文本
        """
        if not self.entries:
            return "无历史记录。"

        entries_to_use = self.entries
        if max_entries is not None:
            entries_to_use = entries_to_use[-max_entries:]

        formatted = "\n".join(
            f"{i + 1}. 用户: {e['user']}\n   助手: {e['assistant']}"
            for i, e in enumerate(entries_to_use)
        )
        return formatted

    def extract_story_summaries_from_time(self, start_time: str) -> str:
        """
        从指定时间开始提取故事摘要

        Args:
            start_time: 起始时间，格式如 "2024-03-15 18:30"
        Returns:
            str: 从指定时间开始的所有故事摘要
        """
        if not self.entries:
            return "无历史记录。"

        # 查找起始时间对应的记录索引
        start_idx = None
        target_time = start_time.strip()

        for idx, entry in enumerate(self.entries):
            entry_time = entry.get("timestamp", "")
            # 比较时间（精确到分钟）
            if entry_time[:16] >= target_time[:16]:
                start_idx = idx
                break

        if start_idx is None:
            return "未找到指定时间或之后的记录。"

        # 提取从起始时间到最后的所有记录中的故事摘要
        summaries = []
        for entry in self.entries[start_idx:]:
            assistant_text = entry.get("assistant", "")
            summary = self._extract_summary_from_assistant(assistant_text)
            if summary:
                summaries.append(summary)

        return "\n\n".join(summaries) if summaries else "未找到故事摘要。"

    def _extract_summary_from_assistant(self, assistant_text: str) -> Optional[str]:
        """
        从助手回复文本中提取故事摘要部分
        匹配格式：##时间戳## 到文本结尾的部分（包含时间戳）

        Args:
            assistant_text: 助手回复的完整文本
        Returns:
            str: 提取的故事摘要，如果没有找到则返回 None
        """
        # 匹配 ##时间戳## 到文本结尾的部分（包含时间戳本身）
        pattern = r'##\d{4}-\d{2}-\d{2} \d{2}:\d{2}##.*'
        match = re.search(pattern, assistant_text, re.DOTALL)
        if match:
            return match.group(0).strip()

        return None

    def save_history(self) -> None:
        """将历史记录保存到文件"""
        try:
            self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存历史失败: {e}")

    def load_history(self) -> None:
        """从文件加载历史记录"""
        if self.HISTORY_FILE.exists():
            try:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    self.entries = json.load(f)
            except Exception as e:
                print(f"[警告] 加载历史失败: {e}")
                self.entries = []

    def clear_history(self) -> None:
        """清空历史记录，并删除文件"""
        self.entries = []
        if self.HISTORY_FILE.exists():
            try:
                self.HISTORY_FILE.unlink()
            except Exception as e:
                print(f"[警告] 删除历史文件失败: {e}")