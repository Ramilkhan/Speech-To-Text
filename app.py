import streamlit as st
import azure.cognitiveservices.speech as speechsdk
import openai
import base64
import tempfile

# ---------------------
#  CONFIGURATION
# ---------------------

AZURE_SPEECH_KEY = "1f9hcUtjhvtdUv2nhtebXYAQ2SaWu8MjEyrZ0hH37jw1n4ETfgXVJQQJ99BKAC3pKaRXJ3w3AAAYACOG3AV4"
AZURE_SPEECH_REGION = "eastasia"

OPENAI_API_KEY = "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"

openai.api_key = OPENAI_API_KEY

st.set_page_config(page_title="Voice AI Chat", layout="wide")

# Black theme UI
st.markdown("""
<style>
body { background-color: #000000; }
.sidebar .sidebar-content { background-color: #111; color: white; }
.css-18e3th9 { background-color: #000 !important; }
.css-1d391kg { background-color: #000 !important; }
h1, h2, p, label { color: white !important; }
</style>
""", unsafe_allow_html=True)

st.title("🎤 Voice AI Assistant")
st.write("Ask anything using your **voice** and get a **spoken answer**.")

# ---------------------
#  SPEECH TO TEXT
# ---------------------

def azure_stt(audio_file_path):
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config, audio_config)

    result = speech_recognizer.recognize_once()
    return result.text


# ---------------------
#  LLM RESPONSE
# ---------------------

def ask_llm(question):
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message["content"]


# ---------------------
#  TEXT TO SPEECH
# ---------------------

def azure_tts(text):
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = "en-US-AriaNeural"

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_audio:
        audio_output = speechsdk.audio.AudioConfig(filename=tmp_audio.name)
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=speech_config,
            audio_config=audio_output
        )
        synthesizer.speak_text_async(text).get()
        return tmp_audio.name


# ---------------------
#  UI - Record Voice
# ---------------------

audio_bytes = st.audio_input("Record your question")

if audio_bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes.read())
        audio_path = tmp.name

    st.write("🎙️ **Recognizing speech...**")
    text = azure_stt(audio_path)
    st.success(f"**You said:** {text}")

    st.write("🤖 **Thinking...**")
    answer = ask_llm(text)
    st.info(answer)

    st.write("🔊 **Generating voice reply...**")
    speech_file = azure_tts(answer)

    with open(speech_file, "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode()

    st.audio(speech_file, format="audio/wav")
