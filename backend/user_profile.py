import json
import os
from datetime import datetime
from config import config


class UserProfileManager:
    def __init__(self):
        self.profiles_path = config.USER_PROFILES_PATH

    def _get_profile_path(self, user_id):
        return os.path.join(self.profiles_path, f"{user_id}.json")

    def get_profile(self, user_id):
        profile_path = self._get_profile_path(user_id)

        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                return json.load(f)
        else:
            return self._create_new_profile(user_id)

    def _create_new_profile(self, user_id):
        profile = {
            "user_id": user_id,
            "created_at": datetime.now().isoformat(),
            "name": None,
            "preferences": {},
            "facts": [],
            "conversation_count": 0,
            "last_interaction": None,
            "personality_adjustments": {
                "formality": 0.5,
                "enthusiasm": 0.7,
                "verbosity": 0.5
            }
        }
        self.save_profile(user_id, profile)
        return profile

    def save_profile(self, user_id, profile):
        profile_path = self._get_profile_path(user_id)
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)

    def update_profile(self, user_id, updates):
        profile = self.get_profile(user_id)
        profile.update(updates)
        profile["last_interaction"] = datetime.now().isoformat()
        self.save_profile(user_id, profile)
        return profile

    def add_fact(self, user_id, fact):
        profile = self.get_profile(user_id)
        if "facts" not in profile:
            profile["facts"] = []

        profile["facts"].append({
            "fact": fact,
            "learned_at": datetime.now().isoformat()
        })
        self.save_profile(user_id, profile)

    def add_preference(self, user_id, category, value):
        profile = self.get_profile(user_id)
        if "preferences" not in profile:
            profile["preferences"] = {}

        profile["preferences"][category] = value
        self.save_profile(user_id, profile)

    def increment_conversation_count(self, user_id):
        profile = self.get_profile(user_id)
        profile["conversation_count"] = profile.get("conversation_count", 0) + 1
        profile["last_interaction"] = datetime.now().isoformat()
        self.save_profile(user_id, profile)