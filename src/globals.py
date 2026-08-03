from pathlib import Path
from typing import Dict, List

ROOT: Path | None = None
PORT = 8080
BLOCKLIST = []
DOWN = False

# Have to be same for both the client and server or may lead to memory corruption
CHUNK_SIZE = 1024 * 1024  # 1MB
SMALL_FILE_SIZE = 5 * 1024 * 1024  # 5MB
CACHE_FILE = "cache.json"

# File storage: {sender: {file_id: {\"chunks\": {chunk_idx: data}, \"metadata\": {...}}}}
file_storage: Dict[str, Dict[str, Dict]] = {}
mailbox: Dict[str, (set[str],List[str])] = {} 