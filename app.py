import streamlit as st
import streamlit.components.v1 as components
import base64
import requests
from openai import OpenAI

# =========================================
# 🔐 CONFIG (PUT YOUR KEYS HERE)
# =========================================
AZURE_KEY = "1f9hcUtjhvtdUv2nhtebXYAQ2SaWu8MjEyrZ0hH37jw1n4ETfgXVJQQJ99BKAC3pKaRXJ3w3AAAYACOG3AV4"
AZURE_REGION = "eastasia"

OPENROUTER_API_KEY = "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"

# =========================================
# STREAMLIT UI
# =========================================
st.set_page_config(page_title="Voice Chat AI", layout="centered")
st.title("🎤 Voice Chat (Azure STT + LLM + Azure TTS)")


# =========================================
# AUDIO RECORDER COMPONENT (WORKS ON STREAMLIT CLOUD)
# =========================================
audio_component = components.declare_component(
    "audio_recorder",
    path="none",
)

html_code = """
<div>
  <button onclick="startRec()">🎙️ Start Recording</button>
  <button onclick="stopRec()">⏹ Stop Recording</button>
</div>

<script>
let mediaRecorder;
let chunks = [];

async function startRec() {
    const stream = await navigator.mediaDevices.getUserMedia({audio:true});
    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = e => chunks.push(e.data);

    mediaRecorder.onstop = e => {
        let blob = new Blob(chunks, {type:'audio/wav'});
        chunks = [];

        let reader = new FileReader();
        reader.onloadend = () => {
            let base64data = reader.result.split(",")[1];
            Streamlit.setComponentValue(base64data);
        };
        reader.readAsDataURL(blob);
    };

    mediaRecorder.start();
}

function stopRec() {
    if (mediaRecorder) mediaRecorder.stop();
}
</script>
"""

# Get audio from component (base64 encoded WAV)
audio_b64 = audio_component(html_code, default=None)

if audio_b64:
    st.success("Audio recorded successfully!")
    audio_bytes = base64.b64decode(audio_b64)
    st.audio(audio_bytes, format="audio/wav")
    st.session_state.audio = audio_bytes


# =========================================
# FUNCTIONS (Azure STT, LLM, Azure TTS)
# =========================================
def azure_stt(audio_bytes):
    url = f"https://{AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "audio/wav"
    }
    r = requests.post(url, headers=headers, data=audio_bytes)
    if r.status_code == 200:
        return r.json().get("DisplayText", "")
    return "STT ERROR: " + r.text


def ask_llm(user_text):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    result = client.chat.completions.create(
        model="google/gemma-3n-e4b-it:free",
        messages=[{"role": "user", "content": user_text}]
    )
    return result.choices[0].message.content


def azure_tts(text):
    url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"

    ssml = f"""
    <speak version='1.0'>
        <voice name='en-US-AriaNeural'>{text}</voice>
    </speak>
    """

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
    }

    r = requests.post(url, headers=headers, data=ssml)
    if r.status_code == 200:
        return r.content
    else:
        return None


# =========================================
# MAIN BUTTON: PROCESS AUDIO
# =========================================
st.write("")

if st.button("Process Audio"):

    if "audio" not in st.session_state:
        st.warning("Please record audio first.")
        st.stop()

    st.info("🔄 Converting speech → text...")
    text = azure_stt(st.session_state.audio)
    st.write("### 🗣️ You said:")
    st.success(text)

    st.info("🤖 Generating LLM response...")
    answer = ask_llm(text)
    st.write("### 🤖 AI says:")
    st.info(answer)

    st.info("🔊 Generating spoken audio...")
    audio_mp3 = azure_tts(answer)

    if audio_mp3:
        st.audio(audio_mp3, format="audio/mp3")
        st.download_button("Download MP3", audio_mp3, "response.mp3")
    else:
        st.error("TTS failed. Check Azure key or region.")
