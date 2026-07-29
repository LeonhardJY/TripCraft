"""清空 Qdrant 中的 travel_guides collection。"""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import QDRANT_COLLECTION_NAME, QDRANT_URL
from qdrant_client import QdrantClient

client = QdrantClient(url=QDRANT_URL, timeout=10)
try:
    client.delete_collection(QDRANT_COLLECTION_NAME)
    print(f"已删除 collection: {QDRANT_COLLECTION_NAME}")
except Exception:
    print(f"collection {QDRANT_COLLECTION_NAME} 不存在，无需删除。")
