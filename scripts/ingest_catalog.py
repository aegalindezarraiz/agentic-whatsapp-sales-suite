"""
Script de ingesta inicial del catálogo de productos.

Uso:
    # Con la API corriendo:
    python scripts/ingest_catalog.py --file data/catalog.json

    # O directamente (sin la API):
    python scripts/ingest_catalog.py --direct --file data/catalog.json
"""

import argparse
import json
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))


def ingest_via_api(file_path: str, api_url: str = "http://localhost:8000") -> None:
    """Ingesta el catálogo a través del endpoint /admin/ingest."""
    import httpx

    with open(file_path, encoding="utf-8") as f:
        products = json.load(f)

    print(f"Ingresando {len(products)} productos vía API...")

    response = httpx.post(
        f"{api_url}/admin/ingest",
        json={"type": "catalog", "data": products},
        timeout=60.0,
    )
    response.raise_for_status()
    result = response.json()
    print(f"✓ Indexados {result['chunks_indexed']} chunks en '{result['collection']}'")


def ingest_direct(file_path: str) -> None:
    """Ingesta el catálogo directamente sin la API (útil en init)."""
    from app.rag import get_rag

    with open(file_path, encoding="utf-8") as f:
        products = json.load(f)

    print(f"Ingresando {len(products)} productos directamente...")
    rag = get_rag()
    count = rag.ingest_catalog(products)
    print(f"✓ Indexados {count} chunks en ChromaDB")


def ingest_document(file_path: str, source_tag: str = "manual") -> None:
    """Ingesta un documento PDF/TXT en la colección de soporte."""
    from app.rag import get_rag

    print(f"Ingresando documento: {file_path}")
    rag = get_rag()
    count = rag.ingest_document(file_path, source_tag=source_tag)
    print(f"✓ Indexados {count} chunks en soporte técnico")


def create_sample_catalog() -> list[dict]:
    """Crea un catálogo de ejemplo para demostración."""
    return [
        {
            "id": "P001",
            "name": "Laptop Pro 15",
            "description": "Laptop de alto rendimiento para profesionales. Ideal para diseño, programación y edición de video.",
            "price": 1299.99,
            "category": "Computadoras",
            "features": ["Intel Core i7 13th Gen", "16GB RAM DDR5", "512GB NVMe SSD", "Pantalla 4K OLED", "Batería 12h"],
            "in_stock": True,
            "shipping": "Envío gratis en 2-3 días hábiles",
        },
        {
            "id": "P002",
            "name": "Mouse Inalámbrico Ergonómico",
            "description": "Mouse ergonómico con diseño vertical para reducir fatiga en uso prolongado.",
            "price": 49.99,
            "category": "Periféricos",
            "features": ["Diseño vertical ergonómico", "2.4GHz inalámbrico", "Receptor USB-C", "Batería recargable 6 meses", "3 niveles DPI"],
            "in_stock": True,
            "shipping": "Envío estándar gratis",
        },
        {
            "id": "P003",
            "name": "Monitor 4K 27 pulgadas",
            "description": "Monitor UHD 4K con panel IPS para diseño gráfico y productividad profesional.",
            "price": 599.99,
            "category": "Monitores",
            "features": ["4K UHD 3840x2160", "Panel IPS", "HDR400", "27 pulgadas", "AMD FreeSync", "2x HDMI + 1x DisplayPort"],
            "in_stock": False,
            "shipping": "Disponible en 2 semanas — Pre-orden disponible",
        },
        {
            "id": "P004",
            "name": "Teclado Mecánico Compacto TKL",
            "description": "Teclado mecánico tenkeyless con switches Cherry MX Red para programadores y gamers.",
            "price": 129.99,
            "category": "Periféricos",
            "features": ["Cherry MX Red switches", "Layout TKL (87 teclas)", "RGB personalizable", "Anti-ghosting completo", "Cable USB-C desmontable"],
            "in_stock": True,
            "shipping": "Envío gratis en 24-48h",
        },
        {
            "id": "P005",
            "name": "Pack Home Office Pro",
            "description": "Bundle completo para trabajo desde casa: laptop + monitor + mouse + teclado.",
            "price": 1899.99,
            "category": "Bundles",
            "features": ["Laptop Pro 15 incluida", "Monitor 27\" incluido", "Mouse ergonómico incluido", "Teclado mecánico incluido", "20% de descuento vs compra individual"],
            "in_stock": True,
            "shipping": "Envío gratis express 24h",
        },
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingesta de catálogo para Agentic Sales Suite")
    parser.add_argument("--file", type=str, help="Ruta al archivo JSON del catálogo")
    parser.add_argument("--doc", type=str, help="Ruta a documento PDF/TXT de soporte")
    parser.add_argument("--direct", action="store_true", help="Ingesta directa sin API")
    parser.add_argument("--sample", action="store_true", help="Crear e ingestar catálogo de ejemplo")
    parser.add_argument("--api-url", default="http://localhost:8000", help="URL de la API")
    parser.add_argument("--source-tag", default="manual", help="Etiqueta para documentos")

    args = parser.parse_args()

    # Configurar variables de entorno mínimas para modo directo
    if args.direct or args.sample:
        os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        os.environ.setdefault("WHATSAPP_PROVIDER", "twilio")
        os.environ.setdefault("TWILIO_ACCOUNT_SID", "placeholder")
        os.environ.setdefault("TWILIO_AUTH_TOKEN", "placeholder")

    if args.sample:
        print("Generando catálogo de ejemplo...")
        sample_data = create_sample_catalog()
        sample_path = "data/sample_catalog.json"
        os.makedirs("data", exist_ok=True)
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)
        print(f"✓ Catálogo guardado en {sample_path}")

        if args.direct:
            ingest_direct(sample_path)
        else:
            ingest_via_api(sample_path, args.api_url)

    elif args.file:
        if args.direct:
            ingest_direct(args.file)
        else:
            ingest_via_api(args.file, args.api_url)

    elif args.doc:
        ingest_document(args.doc, source_tag=args.source_tag)

    else:
        parser.print_help()
        print("\nEjemplos:")
        print("  python scripts/ingest_catalog.py --sample --direct")
        print("  python scripts/ingest_catalog.py --file data/catalog.json")
        print("  python scripts/ingest_catalog.py --doc manuals/product_manual.pdf --source-tag 'manual_v2'")
