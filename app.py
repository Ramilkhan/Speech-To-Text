import streamlit as st
import streamlit.components.v1 as components
import base64
import requests
from openai import OpenAI

# -----------------------------
# CONFIG
# -----------------------------
AZURE_KEY = "1f9hcUtjhvtdUv2nhtebXYAQ2SaWu8MjEyrZ0hH37jw1n4ETfgXVJQQJ99BKAC3pKaRXJ3w3AAAYACOG3AV4"
AZURE_REGION = "eastasia"
OPENROUTER_API_KEY = "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"

st.set_page_config(page_title="Voice Chat", layout="centered")
st.title("🎤 Voice Chat (Azure STT + LLM + Azure TTS)")

# Placeholder for audio output
audio_placeholder = st.empty()

# Hidden HTML Recorder
components.html(
    """
    <html>
    <body>
    <button onclick="startRecording()">🎙️ Start Recording</button>
    <button onclick="stopRecording()">⏹ Stop Recording</button>

    <script>
    let recorder;
    let audioChunks = [];

    async function startRecording() {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recorder = new MediaRecorder(stream);

        recorder.ondataavailable = e => audioChunks.push(e.data);

        recorder.onstop = e => {
            let blob = new Blob(audioChunks, { type: 'audio/wav' });
            audioChunks = [];

            let reader = new FileReader();
            reader.readAsDataURL(blob);
            reader.onloadend = () => {
                const base64data = reader.result.split(',')[1];
                window.parent.postMessage({type: "audio", data: base64data}, "*");
            };
        };

        recorder.start();
    }

    function stopRecording() {
        recorder.stop();
    }

    </script>
    </body>
    </html>
    """,
    height=200,
)

# -----------------------------
# Listening for browser messages
# -----------------------------
audio_b64 = st.experimental_get_query_params().get("audio", [None])[0]

# Use session_state to capture audio
if "audio_input" not in st.session_state:
    st.session_state.audio_input = None


def capture_browser_audio():
    """Reads the audio message posted by HTML."""
    msg = st.experimental_get_query_params()
    return None


# This listens to frontend messages
message = st.experimental_get_query_params()

# Streamlit hack to capture postMessage
st.markdown("""
<script>
window.addEventListener("message", (e) => {
    const audio = e.data;
    if (audio.type === "audio") {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set("audio", audio.data);
        window.location.search = urlParams.toString();
    }
});
</script>
""", unsafe_allow_html=True)


# -----------------------------
# If audio is received
# -----------------------------
audio_param = st.experimental_get_query_params().get("audio", [None])[0]

if audio_param:
    st.session_state.audio_input = base64.b64decode(audio_param)
    st.success("Audio recorded successfully!")
    audio_placeholder.audio(st.session_state.audio_input, format="audio/wav")


# -----------------------------
# Azure STT
# -----------------------------
def azure_stt(audio_bytes):
    url = f"https://{AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "audio/wav"
    }

    resp = requests.post(url, headers=headers, data=audio_bytes)

    if resp.status_code == 200:
        return resp.json().get("DisplayText", "")
    return "STT Error: " + resp.text


# -----------------------------
# LLM response
# -----------------------------
def ask_llm(text):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    completion = client.chat.completions.create(
        model="google/gemma-3n-e4b-it:free",
        messages=[{"role": "user", "content": text}]
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

    r = requests.post(url, headers=headers, data=ssml)
    return r.content if r.status_code == 200 else None


# -----------------------------
# PROCESS BUTTON
# -----------------------------
if st.button("Process Audio"):

    if not st.session_state.audio_input:
        st.warning("Please record audio first.")
    else:
        # Speech → Text
        text = azure_stt(st.session_state.audio_input)
        st.write("### 🗣️ You said:")
        st.success(text)

        # LLM → Answer
        answer = ask_llm(text)
        st.write("### 🤖 AI Response:")
        st.info(answer)

        # Text → Speech
        audio = azure_tts(answer)
        if audio:
            st.audio(audio, format="audio/mp3")
            st.download_button("Download MP3", audio, "answer.mp3")
