import streamlit as st
import requests
import base64
from io import BytesIO
from pydub import AudioSegment
from streamlit_webrtc import webrtc_streamer, WebRtcMode, ClientSettings
from openai import OpenAI


# -------------------------
# CONFIG: API KEYS
# -------------------------
AZURE_KEY = "1f9hcUtjhvtdUv2nhtebXYAQ2SaWu8MjEyrZ0hH37jw1n4ETfgXVJQQJ99BKAC3pKaRXJ3w3AAAYACOG3AV4"
AZURE_REGION = "eastasia"

OPENROUTER_API_KEY = "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"


# -------------------------
# STREAMLIT PAGE
# -------------------------
st.set_page_config(page_title="Voice LLM Chat", page_icon="🎤", layout="centered")
st.title("🎤 Voice Chat with Azure STT + OpenRouter LLM + Azure TTS")


# -------------------------
# AUDIO RECORDING (WebRTC)
# -------------------------
st.subheader("🎙️ Record Your Question")

webrtc_ctx = webrtc_streamer(
    key="speech-record",
    mode=WebRtcMode.SENDONLY,
    client_settings=ClientSettings(
        media_stream_constraints={"audio": True, "video": False}
    )
)


# -------------------------
# Convert Recorded Audio → WAV
# -------------------------
def convert_to_wav(raw_audio):
    audio = AudioSegment.from_file(BytesIO(raw_audio), format="webm")
    wav_io = BytesIO()
    audio.export(wav_io, format="wav")
    return wav_io.getvalue()


# -------------------------
# Azure Speech → Text (STT)
# -------------------------
def azure_stt(audio_bytes):
    stt_url = f"https://{AZURE_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1"

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "audio/wav"
    }

    response = requests.post(stt_url, headers=headers, data=audio_bytes)

    if response.status_code == 200:
        return response.json().get("DisplayText", "")
    else:
        st.error("Azure STT Error: " + response.text)
        return ""


# -------------------------
# LLM via OpenRouter (YOUR CODE)
# -------------------------
def ask_llm(prompt):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    completion = client.chat.completions.create(
        extra_headers={
            "HTTP-Referer": "http://localhost",  
            "X-Title": "Voice LLM App",
        },
        model="google/gemma-3n-e4b-it:free",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


# -------------------------
# Azure Text → Speech (TTS)
# -------------------------
def azure_tts(text):
    tts_url = f"https://{AZURE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1"

    ssml = f"""
    <speak version='1.0'>
        <voice xml:lang='en-US' name='en-US-AriaNeural'>{text}</voice>
    </speak>
    """

    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3"
    }

    response = requests.post(tts_url, headers=headers, data=ssml.encode())

    if response.status_code == 200:
        return response.content
    else:
        st.error("Azure TTS Error: " + response.text)
        return None


# -------------------------
# MAIN LOGIC
# -------------------------
st.write("---")
st.subheader("🎧 Process Your Voice Input")

if st.button("➡️ Convert Speech → LLM → Speech"):

    if not webrtc_ctx or not webrtc_ctx.audio_receiver:
        st.warning("Please record your voice first.")
    else:
        audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=2)

        if not audio_frames:
            st.warning("No audio detected.")
        else:
            raw_audio = audio_frames[0].to_ndarray().tobytes()

            # Convert → WAV
            wav_audio = convert_to_wav(raw_audio)
            st.audio(wav_audio, format="audio/wav")

            # 1️⃣ Speech → Text
            user_text = azure_stt(wav_audio)
            st.write("### 📝 You said:")
            st.success(user_text)

            # 2️⃣ LLM Response
            llm_reply = ask_llm(user_text)
            st.write("### 🤖 LLM Answer:")
            st.info(llm_reply)

            # 3️⃣ Text → Speech
            speech_audio = azure_tts(llm_reply)
            if speech_audio:
                st.audio(speech_audio, format="audio/mp3")
                st.download_button("Download MP3", speech_audio, "llm_answer.mp3")


st.write("---")
st.write("Built with 💚 using Azure + OpenRouter + Streamlit")
