"""
Sistema RAG (Retrieval-Augmented Generation) con ChromaDB.

Provee dos colecciones independientes:
  - product_catalog: catálogo de productos y precios
  - support_docs: manuales y documentación técnica

Uso:
    rag = RAGSystem()
    rag.ingest_catalog([{"name": "Producto X", "price": 50, ...}])
    results = rag.search_catalog("precio de Producto X", k=3)
"""

import json
import os
from pathlib import Path
from typing import Any

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


class RAGSystem:
    """
    Sistema RAG centralizado. Gestiona ingesta y búsqueda en ChromaDB.
    """

    def __init__(self) -> None:
        self._embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )
        self._db_path = Path(settings.vector_db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=64,
            separators=["\n\n", "\n", ".", " "],
        )

        self._catalog_store: Chroma | None = None
        self._docs_store: Chroma | None = None

    # ------------------------------------------------------------------ #
    # Inicialización de stores                                             #
    # ------------------------------------------------------------------ #

    def _get_catalog_store(self) -> Chroma:
        if self._catalog_store is None:
            self._catalog_store = Chroma(
                collection_name=settings.vector_db_collection_catalog,
                embedding_function=self._embeddings,
                persist_directory=str(self._db_path),
            )
        return self._catalog_store

    def _get_docs_store(self) -> Chroma:
        if self._docs_store is None:
            self._docs_store = Chroma(
                collection_name=settings.vector_db_collection_docs,
                embedding_function=self._embeddings,
                persist_directory=str(self._db_path),
            )
        return self._docs_store

    # ------------------------------------------------------------------ #
    # Ingesta                                                              #
    # ------------------------------------------------------------------ #

    def ingest_catalog(self, products: list[dict[str, Any]]) -> int:
        """
        Ingesta una lista de productos en el catálogo vectorial.

        Args:
            products: Lista de dicts con campos del producto.
                      Ejemplo: [{"name": "X", "price": 50, "description": "..."}]

        Returns:
            Número de documentos indexados.
        """
        docs: list[Document] = []
        for product in products:
            text = self._product_to_text(product)
            doc = Document(
                page_content=text,
                metadata={
                    "source": "catalog",
                    "product_id": str(product.get("id", "")),
                    "name": product.get("name", ""),
                    "price": str(product.get("price", "")),
                    "category": product.get("category", ""),
                    "in_stock": str(product.get("in_stock", True)),
                },
            )
            docs.append(doc)

        chunks = self._splitter.split_documents(docs)
        store = self._get_catalog_store()
        store.add_documents(chunks)
        return len(chunks)

    def ingest_catalog_from_json(self, json_path: str) -> int:
        """Ingesta catálogo desde un archivo JSON."""
        with open(json_path, encoding="utf-8") as f:
            products = json.load(f)
        return self.ingest_catalog(products)

    def ingest_document(self, file_path: str, source_tag: str = "docs") -> int:
        """
        Ingesta un documento PDF o TXT en la colección de soporte.

        Args:
            file_path: Ruta al archivo PDF o TXT.
            source_tag: Etiqueta para identificar la fuente.

        Returns:
            Número de chunks indexados.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

        if path.suffix.lower() == ".pdf":
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = source_tag
            doc.metadata["file"] = path.name

        chunks = self._splitter.split_documents(docs)
        store = self._get_docs_store()
        store.add_documents(chunks)
        return len(chunks)

    # ------------------------------------------------------------------ #
    # Búsqueda                                                             #
    # ------------------------------------------------------------------ #

    def search_catalog(self, query: str, k: int = 4) -> str:
        """
        Búsqueda semántica en el catálogo de productos.

        Returns:
            Texto formateado con los resultados más relevantes.
        """
        store = self._get_catalog_store()
        results = store.similarity_search_with_relevance_scores(query, k=k)

        if not results:
            return "No se encontraron productos relevantes en el catálogo."

        output_parts = ["=== RESULTADOS DEL CATÁLOGO ==="]
        for doc, score in results:
            if score < 0.3:  # Filtrar resultados poco relevantes
                continue
            output_parts.append(
                f"\n[Relevancia: {score:.0%}]\n{doc.page_content}"
                f"\n(Fuente: {doc.metadata.get('name', 'Producto')})"
            )

        return "\n".join(output_parts) if len(output_parts) > 1 else "No se encontraron resultados con suficiente relevancia."

    def search_docs(self, query: str, k: int = 4) -> str:
        """
        Búsqueda semántica en la documentación de soporte.

        Returns:
            Texto formateado con los fragmentos más relevantes.
        """
        store = self._get_docs_store()
        results = store.similarity_search_with_relevance_scores(query, k=k)

        if not results:
            return "No se encontró información relevante en la documentación técnica."

        output_parts = ["=== DOCUMENTACIÓN TÉCNICA ==="]
        for doc, score in results:
            if score < 0.3:
                continue
            output_parts.append(
                f"\n[Relevancia: {score:.0%}]\n{doc.page_content}"
                f"\n(Fuente: {doc.metadata.get('file', 'doc')})"
            )

        return "\n".join(output_parts) if len(output_parts) > 1 else "No se encontró documentación relevante."

    # ------------------------------------------------------------------ #
    # Utilidades                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _product_to_text(product: dict[str, Any]) -> str:
        """Convierte un dict de producto en texto para indexar."""
        parts = []
        if name := product.get("name"):
            parts.append(f"Producto: {name}")
        if description := product.get("description"):
            parts.append(f"Descripción: {description}")
        if price := product.get("price"):
            parts.append(f"Precio: ${price}")
        if category := product.get("category"):
            parts.append(f"Categoría: {category}")
        if features := product.get("features"):
            parts.append(f"Características: {', '.join(features) if isinstance(features, list) else features}")
        stock = product.get("in_stock", True)
        parts.append(f"Disponibilidad: {'En stock' if stock else 'Agotado'}")
        if shipping := product.get("shipping"):
            parts.append(f"Envío: {shipping}")
        return "\n".join(parts)

    def collection_stats(self) -> dict[str, int]:
        """Retorna el conteo de documentos en cada colección."""
        catalog_count = self._get_catalog_store()._collection.count()
        docs_count = self._get_docs_store()._collection.count()
        return {"catalog": catalog_count, "support_docs": docs_count}


# Singleton global para reutilizar conexiones
_rag_instance: RAGSystem | None = None


def get_rag() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
    return _rag_instance
