import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .models import Source


TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[a-zA-Z0-9]+")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


@dataclass
class Document:
    title: str
    content: str
    category: str


class LexicalRetriever:
    """Deterministic offline retriever used in demo and tests."""

    def __init__(self, documents: list[Document]):
        self.documents = documents
        self.doc_tokens = [tokenize(doc.title + " " + doc.content) for doc in documents]
        self.df: dict[str, int] = {}
        for tokens in self.doc_tokens:
            for token in set(tokens):
                self.df[token] = self.df.get(token, 0) + 1

    def search(self, query: str, top_k: int = 5) -> list[Source]:
        q_tokens = tokenize(query)
        scored: list[tuple[float, Document]] = []
        total = max(len(self.documents), 1)
        for doc, tokens in zip(self.documents, self.doc_tokens):
            counts: dict[str, int] = {}
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            score = 0.0
            for token in q_tokens:
                tf = counts.get(token, 0)
                if tf:
                    idf = math.log((total + 1) / (self.df.get(token, 0) + 0.5)) + 1
                    score += (1 + math.log(tf)) * idf
            if score > 0:
                scored.append((score, doc))
        scored.sort(key=lambda x: x[0], reverse=True)
        max_score = scored[0][0] if scored else 1.0
        return [
            Source(title=doc.title, score=round(score / max_score, 4), snippet=doc.content[:180])
            for score, doc in scored[:top_k]
        ]


class BgeM3FaissRetriever:
    """Optional production retriever matching the resume stack: BGE-M3 + FAISS."""

    def __init__(self, documents: list[Document], model_name: str):
        try:
            import faiss  # type: ignore
            import numpy as np  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Install requirements-ai.txt to enable BGE-M3 + FAISS") from exc
        self.faiss = faiss
        self.np = np
        self.documents = documents
        self.model = SentenceTransformer(model_name)
        vectors = self.model.encode([d.title + "\n" + d.content for d in documents], normalize_embeddings=True)
        vectors = np.asarray(vectors, dtype="float32")
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def search(self, query: str, top_k: int = 5) -> list[Source]:
        vector = self.model.encode([query], normalize_embeddings=True)
        scores, indices = self.index.search(self.np.asarray(vector, dtype="float32"), top_k)
        return [
            Source(title=self.documents[i].title, score=round(float(score), 4), snippet=self.documents[i].content[:180])
            for score, i in zip(scores[0], indices[0]) if i >= 0
        ]


def load_documents(path: Path) -> list[Document]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Document(**item) for item in raw]

