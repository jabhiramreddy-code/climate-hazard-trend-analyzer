"""Small, persistent NoSQL document cache for a single application worker."""
import json
import os
from pathlib import Path
from threading import RLock
from time import time
from tinydb import Query, TinyDB
from tinydb.storages import Storage


class AtomicJSONStorage(Storage):
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self):
        try:
            with self.path.open(encoding="utf-8") as stream:
                return json.load(stream)
        except FileNotFoundError:
            return None

    def write(self, data):
        temporary = self.path.with_suffix(".tmp")
        try:
            with temporary.open("w", encoding="utf-8") as stream:
                json.dump(data, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class DocumentStore:
    def __init__(self, path):
        self.lock = RLock()
        self.db = TinyDB(path, storage=AtomicJSONStorage)

    def get(self, table, key):
        with self.lock:
            document = self.db.table(table, cache_size=0).get(Query().key == key)
            if document and document["expires_at"] > time():
                return document
        return None

    def put(self, table, key, data, ttl):
        with self.lock:
            collection = self.db.table(table, cache_size=0)
            now = time()
            collection.remove(Query().expires_at <= now)
            collection.upsert({"key": key, "data": data, "created_at": now, "expires_at": now + ttl}, Query().key == key)
            limit = 8 if table == "weather" else 32
            documents = sorted(collection.all(), key=lambda document: document["created_at"])
            if len(documents) > limit:
                collection.remove(doc_ids=[document.doc_id for document in documents[:-limit]])

    def close(self):
        with self.lock:
            self.db.close()

    # shortcut: one worker owns this JSON file; use MongoDB before adding workers or replicas.
