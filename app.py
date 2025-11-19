import streamlit as st
import requests
import base64
from openai import OpenAI


# -----------------------------
# CONFIG KEYS
# -----------------------------
AZURE_KEY = "1f9hcUtjhvtdUv2nhtebXYAQ2SaWu8MjEyrZ0hH37jw1n4ETfgXVJQQJ99BKAC3pKaRXJ3w3AAAYACOG3AV4"
AZURE_REGION = "eastasia"
OPENROUTER_API_KEY = "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"


# -----------------------------
# PAGE SETTINGS
# -----------------------------
st.set_page_config(page_title="Voice LLM", page_icon="🎤", layout="centered")
st.title("🎤 Voice Chat (Azure STT + LLM + Azure TTS)")


# -----------------------------
# JAVASCRIPT MICROPHONE RECORDER
# -----------------------------
st.markdown("""
<script>
let chunks = [];
let recorder;
let stream;

async function startRecording() {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = e => chunks.push(e.data);
    recorder.onstop = e => {
        let blob = new Blob(chunks, { type: 'audio/wav' });
        let reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = () => {
            let base64 = reader.result.split(',')[1];
            window.parent.postMessage({type: 'audio', data: base64}, '*');
        };
        chunks = [];
    };
    recorder.start();
}

function stopRecording() {
    recorder.stop();
    stream.getAudioTracks()[0].stop();
}
</script>

<button onclick="startRecording()">🎙️ Start Recording</button>
<button onclick="stopRecording()">⏹ Stop Recording</button>
""", unsafe_allow_html=True)


# -----------------------------
# CAPTURE BASE64 AUDIO
# -----------------------------
def get_audio_base64():
    from streamlit_javascript import st_javascript
    msg = st_javascript("await new Promise(resolve => window.addEventListener('message', e => resolve(e.data)))")
    if msg and msg.get("type") == "audio":
        return msg["data"]
    return None


audio_b64 = get_audio_base64()

if audio_b64:
    st.success("Audio recorded!")
    audio_bytes = base64.b64decode(audio_b64)
    st.audio(audio_bytes, format="audio/wav")


# -----------------------------
# Azure STT
# -----------------------------
def azure_stt(audio_bytes):
    url = f"https://{AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "audio/wav"
    }

    response = requests.post(url, headers=headers, data=audio_bytes)

    if response.status_code == 200:
        return response.json().get("DisplayText", "")
    else:
        st.error(response.text)
        return ""


# -----------------------------
# OpenRouter LLM
# -----------------------------
def ask_llm(prompt):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY
    )

    completion = client.chat.completions.create(
        model="google/gemma-3n-e4b-it:free",
        messages=[{"role": "user", "content": prompt}]
    )

    return completion.choices[0].message.content


# -----------------------------
# Azure TTS
# -----------------------------
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
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
    }

    response = requests.post(url, headers=headers, data=ssml)

    return response.content if response.status_code == 200 else None


# -----------------------------
# PROCESS BUTTON
# -----------------------------
if st.button("Process Audio"):

    if not audio_b64:
        st.warning("Record something first!")
    else:
        audio_bytes = base64.b64decode(audio_b64)

        # Speech → Text
        text = azure_stt(audio_bytes)
        st.write("### 🗣️ You said:")
        st.success(text)

        # LLM Response
        answer = ask_llm(text)
        st.write("### 🤖 LLM Answer:")
        st.info(answer)

        # Text → Speech
        audio = azure_tts(answer)
        if audio:
            st.audio(audio, format="audio/mp3")
            st.download_button("Download MP3", audio, "response.mp3")
