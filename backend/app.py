import os
import base64
import uuid
import json
from datetime import datetime
import traceback

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from config import config
from memory import MemoryManager
from personality import PersonalityManager
from emotion import EmotionDetector
from user_profile import UserProfileManager
from auth import AuthManager
from threads import ThreadManager  # NEW


# ====================== Chat History Manager (Legacy - kept for backward compatibility) ======================
class ChatHistoryManager:
    def __init__(self, base_path):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def _get_path(self, user_id):
        return os.path.join(self.base_path, f"{user_id}.json")

    def load_history(self, user_id, limit=100):
        path = self._get_path(user_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                history = json.load(f)
            return history[-limit:]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading chat history: {e}")
            return []

    def save_message(self, user_id, role, content):
        path = self._get_path(user_id)
        history = self.load_history(user_id, limit=1000)
        history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(history) > 500:
            history = history[-500:]

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving chat history: {e}")

    def clear_history(self, user_id):
        path = self._get_path(user_id)
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError as e:
                print(f"Error deleting chat history: {e}")


# ====================== AI Client Initialization ======================
app = FastAPI(title="AI Companion API", version="2.0.0")

# Initialize AI client
client = None
ai_provider = None
tts_client = None

try:
    if config.USE_GROQ:
        from groq import Groq

        if not config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env file")

        client = Groq(api_key=config.GROQ_API_KEY)
        ai_provider = "groq"
        print("✅ Groq client initialized successfully (FREE)")

        if config.OPENAI_API_KEY:
            from openai import OpenAI

            tts_client = OpenAI(api_key=config.OPENAI_API_KEY)
            print("✅ OpenAI client initialized for voice features")
        else:
            print("⚠️  No OpenAI key - voice features disabled")
    else:
        from openai import OpenAI

        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in .env file")

        client = OpenAI(api_key=config.OPENAI_API_KEY)
        tts_client = client
        ai_provider = "openai"
        print("✅ OpenAI client initialized successfully")

except Exception as e:
    print(f"❌ Failed to initialize AI client: {e}")
    client = None
    ai_provider = None

# Initialize managers
memory_manager = MemoryManager()
personality_manager = PersonalityManager()
emotion_detector = EmotionDetector()
profile_manager = UserProfileManager()
chat_history_manager = ChatHistoryManager(config.CHAT_HISTORY_PATH)
auth_manager = AuthManager()
thread_manager = ThreadManager()  # NEW

# CORS - Updated for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_URL] if config.FRONTEND_URL != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================== Auth Models ======================
class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str


# ====================== Base Endpoints ======================
@app.get("/")
def root():
    return {
        "message": "AI Companion API",
        "version": "2.0.0",
        "status": "running",
        "ai_provider": ai_provider,
        "ai_configured": client is not None,
        "voice_enabled": tts_client is not None
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy" if client else "degraded",
        "timestamp": datetime.now().isoformat(),
        "ai_provider": ai_provider,
        "voice_features": tts_client is not None
    }


# ====================== Auth Endpoints ======================
@app.post("/auth/register")
async def register(req: RegisterRequest):
    try:
        success, result = auth_manager.register(req.username, req.password, req.email)
        if not success:
            return {"success": False, "message": result}
        return {"success": True, "user_id": result}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /auth/register: {type(e).__name__} - {e}\n")
        return {"success": False, "message": str(e)}


@app.post("/auth/login")
async def login(req: LoginRequest):
    try:
        success, user = auth_manager.authenticate(req.username, req.password)
        if not success:
            return {"success": False, "message": "Invalid credentials"}

        token = auth_manager.create_token(req.username, user["user_id"])
        if not token:
            return {"success": False, "message": "Failed to create session"}

        return {
            "success": True,
            "token": token,
            "user_id": user["user_id"],
            "username": user["username"]
        }
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /auth/login: {type(e).__name__} - {e}\n")
        return {"success": False, "message": "Login failed"}


# ====================== Thread Endpoints (NEW) ======================
@app.get("/threads/{user_id}")
async def get_threads(user_id: str):
    """Get all chat threads for a user"""
    try:
        threads = thread_manager.get_user_threads(user_id)
        return {"success": True, "threads": threads}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /threads: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/threads/{user_id}/create")
async def create_thread(user_id: str, title: str = Form("New Chat")):
    """Create a new chat thread"""
    try:
        thread_id = thread_manager.create_thread(user_id, title)
        return {"success": True, "thread_id": thread_id}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /threads/create: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/threads/{user_id}/{thread_id}")
async def update_thread(user_id: str, thread_id: str, title: str = Form(...)):
    """Update thread title"""
    try:
        thread_manager.update_thread(user_id, thread_id, title=title)
        return {"success": True}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /threads/update: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/threads/{user_id}/{thread_id}")
async def delete_thread(user_id: str, thread_id: str):
    """Delete a chat thread"""
    try:
        thread_manager.delete_thread(user_id, thread_id)
        return {"success": True}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /threads/delete: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/threads/{user_id}/{thread_id}/history")
async def get_thread_history(user_id: str, thread_id: str, limit: int = 50):
    """Get chat history for a specific thread"""
    try:
        history = thread_manager.get_thread_history(user_id, thread_id, limit)
        return {"success": True, "history": history}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /threads/history: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ====================== Chat Endpoint (Updated) ======================
@app.post("/chat")
async def chat(
        user_id: str = Form(...),
        message: str = Form(...),
        thread_id: str = Form(None)  # NEW: Optional thread_id
):
    try:
        if not client:
            raise HTTPException(
                status_code=503,
                detail="AI API is not configured. Please check your API keys in .env file"
            )

        user_profile = profile_manager.get_profile(user_id)
        emotion_data = emotion_detector.detect_emotion(message)
        emotion_guidance = emotion_detector.get_response_guidance(emotion_data)
        relevant_memories = memory_manager.retrieve_relevant_memories(user_id, message)

        system_prompt = personality_manager.get_system_prompt(
            user_profile=user_profile,
            emotion_guidance=emotion_guidance,
            memories=relevant_memories
        )

        personality_adjustment = personality_manager.adjust_for_personality_settings(user_profile)
        if personality_adjustment:
            system_prompt += f"\n\nStyle Adjustment: {personality_adjustment}"

        response = client.chat.completions.create(
            model=config.GPT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.8,
            max_tokens=500
        )

        ai_reply = response.choices[0].message.content

        # Save to thread if thread_id provided, otherwise use legacy chat history
        if thread_id:
            thread_manager.save_thread_message(user_id, thread_id, "user", message)
            thread_manager.save_thread_message(user_id, thread_id, "assistant", ai_reply)
            thread_manager.update_thread(user_id, thread_id, increment_messages=True)
        else:
            chat_history_manager.save_message(user_id, "user", message)
            chat_history_manager.save_message(user_id, "assistant", ai_reply)

        # Store in vector memory
        memory_manager.store_memory(
            user_id,
            f"User: {message}",
            memory_type="user_message",
            metadata={"emotion": emotion_data.get("emotion", "neutral"), "thread_id": thread_id or "default"}
        )

        memory_manager.store_memory(
            user_id,
            f"AI: {ai_reply}",
            memory_type="ai_response",
            metadata={"thread_id": thread_id or "default"}
        )

        profile_manager.increment_conversation_count(user_id)

        return {
            "success": True,
            "reply": ai_reply,
            "emotion": emotion_data,
            "memories_used": len(relevant_memories),
            "conversation_count": user_profile.get("conversation_count", 0) + 1,
            "ai_provider": ai_provider
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"\n🔥 BACKEND ERROR in /chat: {error_type} - {error_msg}")
        print(f"Full traceback:\n{traceback.format_exc()}\n")

        if "AuthenticationError" in error_type or "api_key" in error_msg.lower():
            detail = f"Invalid {ai_provider.upper()} API key. Please check your .env file."
        elif "RateLimitError" in error_type:
            detail = f"{ai_provider.upper()} rate limit exceeded. Please try again in a moment."
        elif "InsufficientQuotaError" in error_type or "quota" in error_msg.lower():
            detail = "Account has no credits. Please add credits or switch to Groq (free)"
        elif "model" in error_msg.lower() and "not found" in error_msg.lower():
            detail = f"AI model '{config.GPT_MODEL}' not available."
        else:
            detail = f"Server error: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)


# ====================== Voice Endpoints ======================
@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    temp_path = None
    try:
        if not tts_client:
            raise HTTPException(
                status_code=503,
                detail="Voice transcription requires OpenAI API. Please add OPENAI_API_KEY to .env"
            )

        temp_filename = f"{uuid.uuid4()}.webm"
        temp_path = os.path.join(config.TEMP_AUDIO_PATH, temp_filename)

        os.makedirs(config.TEMP_AUDIO_PATH, exist_ok=True)

        content = await audio.read()
        with open(temp_path, "wb") as f:
            f.write(content)

        with open(temp_path, "rb") as audio_file:
            transcript = tts_client.audio.transcriptions.create(
                model=config.WHISPER_MODEL,
                file=audio_file,
                language="en"
            )

        return {
            "success": True,
            "text": transcript.text
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"\n🔥 BACKEND ERROR in /transcribe: {error_type} - {error_msg}")
        print(f"Full traceback:\n{traceback.format_exc()}\n")

        if "AuthenticationError" in error_type:
            detail = "Invalid OpenAI API key for transcription"
        elif "quota" in error_msg.lower():
            detail = "OpenAI account has no credits"
        else:
            detail = f"Transcription error: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


@app.post("/tts")
async def text_to_speech(text: str = Form(...)):
    temp_path = None
    try:
        if not tts_client:
            raise HTTPException(
                status_code=503,
                detail="Text-to-speech requires OpenAI API. Please add OPENAI_API_KEY to .env"
            )

        response = tts_client.audio.speech.create(
            model=config.TTS_MODEL,
            voice=config.TTS_VOICE,
            input=text[:4096]
        )

        temp_filename = f"{uuid.uuid4()}.mp3"
        temp_path = os.path.join(config.TEMP_AUDIO_PATH, temp_filename)

        os.makedirs(config.TEMP_AUDIO_PATH, exist_ok=True)
        response.stream_to_file(temp_path)

        with open(temp_path, "rb") as f:
            audio_data = f.read()
            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

        return {
            "success": True,
            "audio_base64": audio_base64
        }

    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"\n🔥 BACKEND ERROR in /tts: {error_type} - {error_msg}")
        print(f"Full traceback:\n{traceback.format_exc()}\n")

        if "AuthenticationError" in error_type:
            detail = "Invalid OpenAI API key for TTS"
        elif "quota" in error_msg.lower():
            detail = "OpenAI account has no credits"
        else:
            detail = f"Text-to-speech error: {error_msg}"

        raise HTTPException(status_code=500, detail=detail)
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ====================== Profile & Memory Endpoints ======================
@app.get("/profile/{user_id}")
async def get_user_profile(user_id: str):
    try:
        profile = profile_manager.get_profile(user_id)
        memory_count = memory_manager.count_memories(user_id)

        return {
            "success": True,
            "profile": profile,
            "total_memories": memory_count
        }
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /profile: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/profile/{user_id}/update")
async def update_user_profile(
        user_id: str,
        name: str = Form(None),
        formality: float = Form(None),
        enthusiasm: float = Form(None),
        verbosity: float = Form(None)
):
    try:
        updates = {}
        if name:
            updates["name"] = name

        personality_adjustments = {}
        if formality is not None:
            personality_adjustments["formality"] = formality
        if enthusiasm is not None:
            personality_adjustments["enthusiasm"] = enthusiasm
        if verbosity is not None:
            personality_adjustments["verbosity"] = verbosity

        if personality_adjustments:
            current_profile = profile_manager.get_profile(user_id)
            existing_adjustments = current_profile.get("personality_adjustments", {})
            existing_adjustments.update(personality_adjustments)
            updates["personality_adjustments"] = existing_adjustments

        profile = profile_manager.update_profile(user_id, updates)

        return {"success": True, "profile": profile}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /profile/update: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{user_id}")
async def get_memories(user_id: str, limit: int = 20):
    try:
        memories = memory_manager.get_recent_memories(user_id, n=limit)
        return {
            "success": True,
            "memories": memories,
            "count": len(memories)
        }
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /memories: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/chat-history/{user_id}")
async def get_chat_history(user_id: str, limit: int = 50):
    try:
        history = chat_history_manager.load_history(user_id, limit)
        return {"success": True, "history": history}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /chat-history: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/chat-history/{user_id}")
async def clear_chat_history(user_id: str):
    try:
        chat_history_manager.clear_history(user_id)
        return {"success": True}
    except Exception as e:
        print(f"\n🔥 BACKEND ERROR in /chat-history delete: {type(e).__name__} - {e}\n")
        raise HTTPException(status_code=500, detail=str(e))


# ====================== Startup Event ======================
@app.on_event("startup")
async def startup_event():
    print("\n" + "=" * 60)
    print("🚀 AI Companion API Starting...")
    print("=" * 60)

    if ai_provider == "groq":
        if config.GROQ_API_KEY:
            masked_key = config.GROQ_API_KEY[:8] + "..." + config.GROQ_API_KEY[-4:]
            print(f"✅ Groq API Key: {masked_key} (FREE)")
        else:
            print("❌ Groq API Key: NOT SET")

    if config.OPENAI_API_KEY:
        masked_key = config.OPENAI_API_KEY[:10] + "..." + config.OPENAI_API_KEY[-4:]
        if ai_provider == "openai":
            print(f"✅ OpenAI API Key: {masked_key}")
        else:
            print(f"✅ OpenAI API Key: {masked_key} (for voice only)")
    else:
        if ai_provider != "groq":
            print("❌ OpenAI API Key: NOT SET")

    print(f"✅ AI Provider: {ai_provider.upper() if ai_provider else 'NONE'}")
    print(f"✅ Voice Features: {'Enabled' if tts_client else 'Disabled'}")
    print(f"✅ Memory DB: {config.MEMORY_DB_PATH}")
    print(f"✅ User Profiles: {config.USER_PROFILES_PATH}")
    print(f"✅ Chat History: {config.CHAT_HISTORY_PATH}")
    print(f"✅ Threads: {config.THREADS_PATH}")
    print(f"✅ Users DB: {config.USERS_PATH}")
    print(f"✅ Temp Audio: {config.TEMP_AUDIO_PATH}")
    print(f"✅ Chat Model: {config.GPT_MODEL}")

    if tts_client:
        print(f"✅ Whisper Model: {config.WHISPER_MODEL}")
        print(f"✅ TTS Voice: {config.TTS_VOICE}")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True
    )