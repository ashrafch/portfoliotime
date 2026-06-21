"""
RAG Ingestion — job offline (R3: mai chiamato durante una HTTP request).

Legge tutti i file da knowledge-base/, li chunka su separatori H2,
crea gli embedding e li indicizza in Qdrant.

Eseguire dopo ogni modifica a knowledge-base/:
    cd apps/api && python rag/ingestion.py
"""

import os
import sys
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, StorageContext
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core.node_parser import MarkdownNodeParser
import qdrant_client

# Percorso knowledge-base relativo alla root del progetto
KB_PATH = Path(__file__).parent.parent.parent.parent / "knowledge-base"
COLLECTION_NAME = "portfoliotime_kb"


def run_ingestion(qdrant_url: str = "http://localhost:6333") -> None:
    """Legge knowledge-base/, crea embedding e popola Qdrant.

    R3: Questa funzione è esclusivamente build-time.
    NON chiamarla mai in una route FastAPI.
    """
    if not KB_PATH.exists():
        print(f"[ERRORE] knowledge-base non trovato in: {KB_PATH}")
        sys.exit(1)

    print(f"[ingestion] Lettura da: {KB_PATH}")
    client = qdrant_client.QdrantClient(url=qdrant_url)

    # Rimuove la collezione precedente per ricrearne una pulita
    if client.collection_exists(COLLECTION_NAME):
        client.delete_collection(COLLECTION_NAME)
        print(f"[ingestion] Collezione '{COLLECTION_NAME}' eliminata per reindicizzazione.")

    vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    documents = SimpleDirectoryReader(
        input_dir=str(KB_PATH),
        recursive=True,
        required_exts=[".md"],
    ).load_data()

    print(f"[ingestion] Documenti trovati: {len(documents)}")

    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_documents(documents)
    print(f"[ingestion] Chunk creati: {len(nodes)}")

    VectorStoreIndex(nodes, storage_context=storage_context)
    print(f"[ingestion] ✓ Indicizzazione completata in '{COLLECTION_NAME}'")


if __name__ == "__main__":
    from config import get_settings
    settings = get_settings()
    run_ingestion(qdrant_url=settings.qdrant_url)
