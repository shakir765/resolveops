from pathlib import Path
from typing import Any

from resolveops_core.config import settings


class KnowledgeBase:
    def __init__(self, persist_dir: str | None = None):
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            import chromadb

            client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = client.get_or_create_collection("resolveops_kb")
        return self._collection

    def ingest_documents(self, documents: list[dict[str, str]]) -> int:
        collection = self._get_collection()
        ids = [doc["id"] for doc in documents]
        texts = [doc["content"] for doc in documents]
        metadatas = [{"source": doc.get("source", "runbook")} for doc in documents]
        collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        return len(documents)

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        collection = self._get_collection()
        if collection.count() == 0:
            return []
        result = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            {"content": doc, "metadata": meta or {}, "score": 1 - (dist or 0)}
            for doc, meta, dist in zip(documents, metadatas, distances)
        ]


kb = KnowledgeBase()
