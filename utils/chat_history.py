# utils/chat_history.py

import re
import json
from pathlib import Path

class ChatHistory:
    """管理聊天历史摘要"""
    TIMESTAMP_PATTERN = re.compile(r"##[\d\- :]+##([\s\S]+)")
    # 根目录下的 log/history.json
    HISTORY_FILE = Path(__file__).resolve().parent.parent / "log/history.json"
    # HISTORY_FILE = Path("log/history.json")

    def __init__(self, max_entries: int = 10):
        self.entries = []
        self.max_entries = max_entries
        # 初始化时尝试加载已有历史
        self.load_history()

    def add_entry(self, summary: str) -> None:
        """向聊天历史中添加新的摘要条目"""
        self.entries.append(summary)
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]
        self.save_history()  # 添加后立即保存

    def format_history(self) -> str:
        """格式化聊天历史为可读文本"""
        if not self.entries:
            return "无历史记录。"
        return "\n".join(f"{idx}. {entry.strip()}" for idx, entry in enumerate(self.entries, 1))

    def save_history(self) -> None:
        """将历史记录保存到文件"""
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.entries, f, ensure_ascii=False, indent=2)

    def load_history(self) -> None:
        """从文件加载历史记录"""
        if self.HISTORY_FILE.exists():
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                self.entries = json.load(f)
