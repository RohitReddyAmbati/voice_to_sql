# voice_app.py
import os
import wave
import tempfile
import sounddevice as sd
import pyttsx3

from faster_whisper import WhisperModel

from app.intent import classify_intent
from app.pipeline import answer_question
from app.profile import profile_db
from app.memory import add_memory, recall_memory

SAMPLE_RATE = int(os.getenv("VOICE_SR", "16000"))
CHANNELS = 1
REC_SECONDS = int(os.getenv("VOICE_SECONDS", "8"))
TTS_ENABLED = os.getenv("VOICE_TTS", "1") != "0"

# STT model settings (change FW_MODEL env to tiny|base|small|medium|large-v3)
FW_MODEL = os.getenv("FW_MODEL", "large-v3")
FW_DEVICE = os.getenv("FW_DEVICE", "cpu")       # cpu | cuda (if you have it)
FW_COMPUTE = os.getenv("FW_COMPUTE", "int8")    # int8 is fast & light on CPU

print(f"[INFO] Loading faster-whisper model: {FW_MODEL} ({FW_DEVICE}, {FW_COMPUTE})")
stt_model = WhisperModel(FW_MODEL, device=FW_DEVICE, compute_type=FW_COMPUTE)

def record_voice(seconds: int = REC_SECONDS, path: str = "data/tmp_voice.wav") -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    print(f"Recording for {seconds} seconds... (Ctrl+C to abort)")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16")
    sd.wait()
    with wave.open(path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    print(f"Saved: {path}")
    return path

def speak_text(text: str):
    if not TTS_ENABLED:
        return
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def transcribe_wav(path: str) -> str:
    segments, info = stt_model.transcribe(path, beam_size=1)  
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text or "(no speech detected)"

def handle_question(q: str) -> str:
    intent = classify_intent(q)
    print(f"[Intent] {intent}")
    if intent == "PROFILE":
        prof = profile_db()
        add_memory(q, prof if isinstance(prof, str) else "profile generated")
        return "I generated a profile of your database. Use the text app to read details."
    elif intent in ("SQL_DATA", "SQL_SCHEMA"):
        res = answer_question(q)
        if not res.get("ok"):
            msg = f"Error: {res.get('error') or 'unknown'}"
            add_memory(q, msg)
            return msg
        add_memory(q, res["text"])
        print("\n[Text Answer]\n", res["text"])
        print("\n[Preview Rows]")
        if res.get("columns"):
            print(res["columns"])
        for r in res.get("rows", [])[:10]:
            print(r)
        print("\n[SQL Used]\n", res["sql"])
        return res["text"]
    else:
        ans = recall_memory(q)
        add_memory(q, ans)
        return ans

def main():
    print("Voice NL2SQL Assistant (Ctrl+C to quit)")
    while True:
        try:
            wav = record_voice()
            text = transcribe_wav(wav)
            print(f"\n[You said] {text}\n")
            answer = handle_question(text)
            print(f"\n[Assistant]\n{answer}\n")
            speak_text(answer)
        except KeyboardInterrupt:
            print("\n Exiting.")
            break
        except Exception as e:
            print("[ERROR]", e)

if __name__ == "__main__":
    main()
