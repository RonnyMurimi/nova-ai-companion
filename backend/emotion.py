from transformers import pipeline
import torch


class EmotionDetector:
    def __init__(self):
        try:
            self.classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                top_k=None
            )
            self.use_transformer = True
        except Exception as e:
            print(f"Warning: Could not load transformer model: {e}")
            print("Falling back to keyword-based emotion detection")
            self.use_transformer = False

        self.emotion_keywords = {
            "joy": ["happy", "great", "excited", "wonderful", "amazing", "love", "fantastic"],
            "sadness": ["sad", "down", "depressed", "hurt", "lonely", "cry", "terrible"],
            "anger": ["angry", "mad", "frustrated", "annoyed", "furious", "hate"],
            "fear": ["scared", "afraid", "anxious", "worried", "nervous", "terrified"],
            "surprise": ["wow", "surprising", "shocked", "unexpected", "amazing"],
            "neutral": []
        }

    def detect_emotion(self, text):
        if self.use_transformer:
            return self._detect_with_transformer(text)
        else:
            return self._detect_with_keywords(text)

    def _detect_with_transformer(self, text):
        try:
            results = self.classifier(text)[0]
            top_emotion = max(results, key=lambda x: x['score'])

            return {
                "emotion": top_emotion['label'],
                "confidence": top_emotion['score'],
                "all_emotions": {r['label']: r['score'] for r in results}
            }
        except Exception as e:
            print(f"Error in transformer emotion detection: {e}")
            return self._detect_with_keywords(text)

    def _detect_with_keywords(self, text):
        text_lower = text.lower()
        scores = {emotion: 0 for emotion in self.emotion_keywords.keys()}

        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[emotion] += 1

        detected_emotion = max(scores, key=scores.get)
        if scores[detected_emotion] == 0:
            detected_emotion = "neutral"

        return {
            "emotion": detected_emotion,
            "confidence": 0.7 if scores[detected_emotion] > 0 else 0.5,
            "all_emotions": scores
        }

    def get_response_guidance(self, emotion_data):
        emotion = emotion_data["emotion"]

        guidance = {
            "joy": "Match their positive energy. Be enthusiastic and encouraging.",
            "sadness": "Respond with empathy and gentle support. Offer comfort.",
            "anger": "Stay calm and understanding. Help them process their feelings.",
            "fear": "Be reassuring and supportive. Provide calm guidance.",
            "surprise": "Share in their excitement or concern as appropriate.",
            "neutral": "Respond naturally and helpfully."
        }

        return guidance.get(emotion, guidance["neutral"])