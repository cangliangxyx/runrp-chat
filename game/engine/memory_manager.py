# engine/memory_manager.py
import os
import json
import chromadb
from sentence_transformers import SentenceTransformer

class MemoryManager:
    def __init__(self, db_path="data/memory_db", collection_name="story_memory"):
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(collection_name)
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

    def add_memory(self, text: str, metadata: dict = None):
        """喂样本：把新的剧情、人物设定、事件加入记忆库"""
        if not text.strip():
            return False

        embedding = self.embedder.encode([text]).tolist()[0]
        doc_id = f"id_{hash(text)}"
        self.collection.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata or {}]
        )
        return True

    def query_memory(self, query: str, top_k: int = 3):
        """检索与当前场景相关的记忆片段"""
        query_emb = self.embedder.encode([query]).tolist()
        results = self.collection.query(query_embeddings=query_emb, n_results=top_k)
        if results and results.get("documents"):
            return results["documents"][0]
        return []

    def build_prompt_context(self, query: str, base_prompt: str, top_k: int = 3):
        """根据检索结果拼接 Prompt，让模型参考记忆"""
        related_memories = self.query_memory(query, top_k)
        if not related_memories:
            return base_prompt
        memory_text = "\n\n".join(related_memories)
        return (
            f"以下是你过去的记忆与设定，请结合它们生成回应：\n{memory_text}\n\n"
            f"---\n当前请求：{base_prompt}"
        )

    def export_all_memories(self, export_path="data/memory_db/all_memories.json"):
        """导出所有记忆数据"""
        data = self.collection.get()
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)