import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


class ChatHistory:
    """管理聊天历史（存储完整对话，简洁版）"""

    HISTORY_FILE = Path(__file__).resolve().parent.parent / "log/chat_history.json"

    def __init__(self, max_entries: int = 50):
        self.max_entries = max_entries
        self.entries: List[Dict[str, Any]] = []
        self.load_history()

    def add_entry(self, user: str, assistant: str) -> None:
        """新增一条对话记录"""
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": user.strip(),
            "assistant": assistant.strip()
        }
        self.entries.append(entry)

        # 控制记录数量
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        self.save_history()

    def format_history(self) -> str:
        """格式化历史记录，便于拼接 prompt"""
        if not self.entries:
            return "无历史记录。"

        return "\n".join(
            f"{i+1}. 用户: {e['user']}\n   助手: {e['assistant']}"
            for i, e in enumerate(self.entries)
        )

    def save_history(self) -> None:
        """保存到文件"""
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def load_history(self) -> None:
        """从文件加载"""
        if self.HISTORY_FILE.exists():
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                self.entries = json.load(f)

    def clear_history(self) -> None:
        """清空历史"""
        self.entries = []
        if self.HISTORY_FILE.exists():
            self.HISTORY_FILE.unlink()
