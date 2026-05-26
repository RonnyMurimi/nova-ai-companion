import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
import json
from config import config


class MemoryManager:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=config.MEMORY_DB_PATH)
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collection = self.client.get_or_create_collection(
            name=config.MEMORY_COLLECTION_NAME,
            embedding_function=self.embedding_func
        )

    def store_memory(self, user_id, text, memory_type="conversation", metadata=None):
        if metadata is None:
            metadata = {}

        timestamp = datetime.now().isoformat()
        doc_id = f"{user_id}_{timestamp}_{memory_type}"

        full_metadata = {
            "user_id": user_id,
            "type": memory_type,
            "timestamp": timestamp,
            **metadata
        }

        try:
            self.collection.add(
                documents=[text],
                metadatas=[full_metadata],
                ids=[doc_id]
            )
            return True
        except Exception as e:
            print(f"Error storing memory: {e}")
            return False

    def retrieve_relevant_memories(self, user_id, query, n_results=None):
        if n_results is None:
            n_results = config.MAX_MEMORIES_RETRIEVED

        try:
            all_memories = self.collection.get(
                where={"user_id": user_id}
            )

            if not all_memories or not all_memories["ids"]:
                return []

            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, len(all_memories["ids"])),
                where={"user_id": user_id}
            )

            memories = []
            if results and "documents" in results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })

            return memories
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []

    def get_recent_memories(self, user_id, n=5):
        try:
            all_memories = self.collection.get(
                where={"user_id": user_id}
            )

            if not all_memories or not all_memories["ids"]:
                return []

            memories_with_time = []
            for i, doc_id in enumerate(all_memories["ids"]):
                memories_with_time.append({
                    "text": all_memories["documents"][i],
                    "metadata": all_memories["metadatas"][i],
                    "id": doc_id
                })

            sorted_memories = sorted(
                memories_with_time,
                key=lambda x: x["metadata"].get("timestamp", ""),
                reverse=True
            )

            return sorted_memories[:n]
        except Exception as e:
            print(f"Error getting recent memories: {e}")
            return []

    def count_memories(self, user_id):
        try:
            all_memories = self.collection.get(
                where={"user_id": user_id}
            )
            return len(all_memories["ids"]) if all_memories else 0
        except Exception as e:
            print(f"Error counting memories: {e}")
            return 0