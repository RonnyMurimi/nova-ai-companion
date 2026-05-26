class PersonalityManager:
    def __init__(self):
        self.base_personality = {
            "name": "Nova",
            "role": "AI companion and assistant",
            "core_traits": [
                "empathetic",
                "curious",
                "supportive",
                "intelligent",
                "emotionally aware"
            ],
            "communication_style": "warm, natural, and conversational",
            "values": [
                "understanding the user deeply",
                "providing thoughtful responses",
                "maintaining continuity across conversations",
                "respecting boundaries",
                "being helpful without being overbearing"
            ]
        }

    def get_system_prompt(self, user_profile=None, emotion_guidance=None, memories=None):
        prompt = f"""You are {self.base_personality['name']}, an {self.base_personality['role']}.

Core Traits: {', '.join(self.base_personality['core_traits'])}
Communication Style: {self.base_personality['communication_style']}

Your Values:
{self._format_list(self.base_personality['values'])}

"""

        if user_profile:
            prompt += self._format_user_context(user_profile)

        if memories and len(memories) > 0:
            prompt += "\nRelevant Past Conversations:\n"
            for memory in memories[:5]:
                prompt += f"- {memory['text']}\n"
            prompt += "\n"

        if emotion_guidance:
            prompt += f"\n🎭 Current Emotional Context: {emotion_guidance}\n"

        prompt += """
Guidelines:
- Remember and reference past conversations naturally
- Show growth and continuity in your relationship with the user
- Adapt your tone based on the user's emotional state
- Ask follow-up questions to show genuine interest
- Keep responses engaging but concise unless more detail is requested
- Be yourself - don't be overly formal or robotic
- If you don't remember something, it's okay to ask for clarification
"""

        return prompt

    def _format_user_context(self, profile):
        context = "\n📋 User Context:\n"

        if profile.get("name"):
            context += f"- User's name: {profile['name']}\n"

        if profile.get("conversation_count", 0) > 0:
            context += f"- You've had {profile['conversation_count']} conversations together\n"

        if profile.get("facts"):
            context += "\nThings you know about the user:\n"
            for fact_entry in profile["facts"][-10:]:
                context += f"- {fact_entry['fact']}\n"

        if profile.get("preferences"):
            context += "\nUser preferences:\n"
            for category, value in profile["preferences"].items():
                context += f"- {category}: {value}\n"

        return context + "\n"

    def _format_list(self, items):
        return "\n".join([f"- {item}" for item in items])

    def adjust_for_personality_settings(self, profile):
        adjustments = profile.get("personality_adjustments", {})

        guidance = []

        formality = adjustments.get("formality", 0.5)
        if formality > 0.7:
            guidance.append("Maintain a more formal and professional tone")
        elif formality < 0.3:
            guidance.append("Be casual and relaxed in your communication")

        enthusiasm = adjustments.get("enthusiasm", 0.7)
        if enthusiasm > 0.7:
            guidance.append("Show more energy and enthusiasm in your responses")
        elif enthusiasm < 0.3:
            guidance.append("Keep a calm and measured tone")

        verbosity = adjustments.get("verbosity", 0.5)
        if verbosity > 0.7:
            guidance.append("Provide detailed, comprehensive responses")
        elif verbosity < 0.3:
            guidance.append("Keep responses brief and to the point")

        return " ".join(guidance) if guidance else None