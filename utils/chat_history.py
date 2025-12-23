# utils/chat_history.py

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

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

    def reload(self) -> None:
        """
        重新从文件加载最新的聊天记录。
        适用于文件被外部修改后需要手动同步内存的情况。
        """
        before_count = len(self.entries)
        logger.info(f"[ChatHistory] 重新加载历史记录，当前内存中有 {before_count} 条记录。")
        self.load_history()
        after_count = len(self.entries)
        logger.info(f"[ChatHistory] 重新加载完成，最新记录条数：{after_count}。")

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
            str: 提取的故事星记忆回廊，如果没有找到则返回 None
        """
        # 匹配 ##时间戳## 到文本结尾的部分（包含时间戳本身）
        # pattern = r'**\s*动态角色状态机-\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\s*##.*'
        pattern = r'\动态角色状态机-\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}[\s\S]*$'
        match = re.search(pattern, assistant_text, re.DOTALL)
        print("match = ",match)
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

    def is_empty(self) -> bool:
        """
        判断历史记录是否为空
        Returns:
            bool: True 表示没有任何历史记录
        """
        return len(self.entries) == 0

    def remove_last_entry(self) -> None:
        """
        删除最后一条对话记录

        如果历史为空，不执行任何操作。
        删除后会自动保存到文件。
        """
        if not self.entries:
            logger.warning("[ChatHistory] 无法删除：当前没有任何历史记录。")
            return

        removed_entry = self.entries.pop()  # 删除最后一条
        logger.info(
            f"[ChatHistory] 已删除最后一条记录，时间: {removed_entry.get('timestamp', '未知')}，"
            f"用户内容: {removed_entry.get('user', '')[:30]}..."
        )

        self.save_history()


if __name__ == "__main__":
    history = ChatHistory()
    history.remove_last_entry()  # 删除最新一条记录