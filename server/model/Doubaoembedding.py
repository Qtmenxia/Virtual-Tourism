from langchain_core.embeddings import Embeddings
import hashlib
import numpy as np

class DoubaoEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        # 使用 hash 模拟生成 embedding（建议替换为本地真实模型）
        h = hashlib.sha256(text.encode()).hexdigest()
        vec = [int(h[i:i+4], 16) % 1000 / 1000.0 for i in range(0, 64, 4)]
        return vec
