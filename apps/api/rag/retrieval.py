"""
RAG Retrieval — interroga Qdrant a runtime per contestualizzare la narrativa AI.

R3: Qdrant viene solo letto qui, mai scritto.
R1: L'output di retrieve() va a Claude come contesto, non come fonte di numeri.
"""

from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
import qdrant_client
from functools import lru_cache
from config import get_settings

COLLECTION_NAME = "portfoliotime_kb"
TOP_K = 5


@lru_cache(maxsize=1)
def _get_index() -> VectorStoreIndex:
    """Carica l'indice Qdrant una volta sola (singleton per processo)."""
    settings = get_settings()
    client = qdrant_client.QdrantClient(url=settings.qdrant_url)
    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    return VectorStoreIndex.from_vector_store(vector_store, storage_context=storage_context)


def retrieve(query: str, top_k: int = TOP_K) -> list[str]:
    """Recupera i chunk più rilevanti dalla knowledge-base per una query.

    Args:
        query: Domanda o contesto da usare per la ricerca semantica.
        top_k: Numero massimo di chunk da restituire.

    Returns:
        Lista di testi (chunk) ordinati per rilevanza.
    """
    index = _get_index()
    retriever = index.as_retriever(similarity_top_k=top_k)
    nodes = retriever.retrieve(query)
    return [node.get_content() for node in nodes]
