# engine/memory_manager.py
import os
import json
import logging
import chromadb
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# import os
#
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
db_path = os.path.join(BASE_DIR, "data", "memory_db")
# self.client = chromadb.PersistentClient(path=db_path)

class MemoryManager:
    def __init__(self, db_path=db_path, collection_name="story_memory"):
        os.makedirs(db_path, exist_ok=True)
        # self.client = chromadb.PersistentClient(path=db_path)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
        logging.info(f"MemoryManager initialized with db_path='{db_path}', collection='{collection_name}'")

    def add_memory(self, text: str, metadata: dict = None):
        """喂样本：把新的剧情、人物设定、事件加入记忆库"""
        if not text.strip():
            logging.warning("尝试添加空文本记忆，操作被忽略")
            return False

        try:
            embedding = self.embedder.encode([text]).tolist()[0]
            doc_id = f"id_{hash(text)}"
            safe_metadata = metadata if isinstance(metadata, dict) and metadata else {"source": "unknown"}
            self.collection.add(
                ids=[doc_id],
                documents=[text],
                embeddings=[embedding],
                metadatas=[safe_metadata]
            )
            logging.info(f"记忆已添加: id={doc_id}, text='{text[:30]}...'")
            return True
        except Exception as e:
            logging.error(f"添加记忆失败: {e}")
            return False

    def query_memory(self, query: str, top_k: int = 3):
        """检索与当前场景相关的记忆片段"""
        try:
            query_emb = self.embedder.encode([query]).tolist()
            results = self.collection.query(query_embeddings=query_emb, n_results=top_k)
            if results and results.get("documents"):
                docs = results["documents"][0]
                logging.info(f"查询到 {len(docs)} 条相关记忆")
                return docs
        except Exception as e:
            logging.error(f"查询记忆失败: {e}")
        return []

    def build_prompt_context(self, query: str, base_prompt: str, top_k: int = 3):
        """根据检索结果拼接 Prompt，让模型参考记忆"""
        related_memories = self.query_memory(query, top_k)
        if not related_memories:
            logging.info("未找到相关记忆，返回原始 prompt")
            return base_prompt
        memory_text = "\n\n".join(related_memories)
        logging.info("成功构建基于记忆的 prompt")
        return (
            f"以下是你过去的记忆与设定，请结合它们生成回应：\n{memory_text}\n\n"
            f"---\n当前请求：{base_prompt}"
        )

    def export_all_memories(self, export_path="data/memory_db/all_memories.json"):
        """导出所有记忆数据"""
        try:
            data = self.collection.get()
            os.makedirs(os.path.dirname(export_path), exist_ok=True)
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"所有记忆已导出到 {export_path}")
        except Exception as e:
            logging.error(f"导出记忆失败: {e}")

def main():
    # 绝对路径初始化 MemoryManager
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "data", "memory_db")
    memory_manager = MemoryManager(db_path=db_path, collection_name="story_memory")

    # 导出所有记忆
    memory_manager.export_all_memories(export_path=os.path.join(db_path, "all_memories.json"))
    print("\n已导出所有记忆到", os.path.join(db_path, "all_memories.json"))

if __name__ == "__main__":
    main()
