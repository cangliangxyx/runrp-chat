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
        # pattern = r'##\d{4}-\d{2}-\d{2} \d{2}:\d{2}##.*'
        pattern = r'##\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*##.*'
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