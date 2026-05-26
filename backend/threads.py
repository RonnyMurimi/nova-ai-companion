import json
import os
import uuid
from datetime import datetime
from config import config


class ThreadManager:
    def __init__(self):
        self.threads_path = config.THREADS_PATH
        os.makedirs(self.threads_path, exist_ok=True)

    def _get_user_threads_path(self, user_id):
        return os.path.join(self.threads_path, f"{user_id}_threads.json")

    def get_user_threads(self, user_id):
        """Get all threads for a user"""
        path = self._get_user_threads_path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                threads = json.load(f)
            threads.sort(key=lambda x: x.get('last_updated', ''), reverse=True)
            return threads
        except (json.JSONDecodeError, IOError):
            return []

    def create_thread(self, user_id, title="New Chat"):
        """Create a new chat thread"""
        threads = self.get_user_threads(user_id)
        thread_id = str(uuid.uuid4())
        new_thread = {
            "thread_id": thread_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "message_count": 0
        }
        threads.append(new_thread)
        self._save_threads(user_id, threads)
        return thread_id

    def update_thread(self, user_id, thread_id, title=None, increment_messages=False):
        """Update thread metadata"""
        threads = self.get_user_threads(user_id)
        for thread in threads:
            if thread["thread_id"] == thread_id:
                if title:
                    thread["title"] = title
                if increment_messages:
                    thread["message_count"] = thread.get("message_count", 0) + 1
                thread["last_updated"] = datetime.now().isoformat()
                break
        self._save_threads(user_id, threads)

    def delete_thread(self, user_id, thread_id):
        """Delete a thread"""
        threads = self.get_user_threads(user_id)
        threads = [t for t in threads if t["thread_id"] != thread_id]
        self._save_threads(user_id, threads)

        history_path = self._get_thread_history_path(user_id, thread_id)
        if os.path.exists(history_path):
            os.remove(history_path)

    def _save_threads(self, user_id, threads):
        path = self._get_user_threads_path(user_id)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)

    def _get_thread_history_path(self, user_id, thread_id):
        return os.path.join(config.CHAT_HISTORY_PATH, f"{user_id}_{thread_id}.json")

    def get_thread_history(self, user_id, thread_id, limit=100):
        """Get chat history for a specific thread"""
        path = self._get_thread_history_path(user_id, thread_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history[-limit:]
        except (json.JSONDecodeError, IOError):
            return []

    def save_thread_message(self, user_id, thread_id, role, content):
        """Save a message to a thread"""
        path = self._get_thread_history_path(user_id, thread_id)
        history = self.get_thread_history(user_id, thread_id, limit=1000)
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(history) > 500:
            history = history[-500:]

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def clear_thread_history(self, user_id, thread_id):
        """Clear chat history for a thread"""
        path = self._get_thread_history_path(user_id, thread_id)
        if os.path.exists(path):
            os.remove(path)