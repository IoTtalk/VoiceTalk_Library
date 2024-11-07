import io
import pandas as pd
from google.oauth2 import service_account
from google.cloud import speech

def SpeechToText(client_file, audio_file):
    credentials = service_account.Credentials.from_service_account_file(client_file)
    client = speech.SpeechClient(credentials = credentials)
    with io.open(audio_file, 'rb') as f:
        content=f.read()
        audio = speech.RecognitionAudio(content = content)

    config = speech.RecognitionConfig(
        encoding = speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz = 48000,
        language_code='en-US',
        model="telephony_short",
        audio_channel_count=1,
        enable_word_confidence=True,
        enable_word_time_offsets=True
    )
    operation = client.long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=90)
    r = response.results[0]
    return r.alternatives[0].transcript