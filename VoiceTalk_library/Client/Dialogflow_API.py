import os
import config
from google.cloud import dialogflow_v2 as dialogflow
from google.api_core.exceptions import InvalidArgument
# DialogFlow 相關環境
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config.Dia_API_key

def detect_intent_audio(project_id, session_id, audio_file_path, language_code):
    """Returns the result of detect intent with an audio file as input.
    Using the same `session_id` between requests allows continuation
    of the conversation."""
    session_client = dialogflow.SessionsClient()
    # Note: hard coding audio_encoding and sample_rate_hertz for simplicity.
    audio_encoding = dialogflow.AudioEncoding.AUDIO_ENCODING_LINEAR_16
    sample_rate_hertz = 48000  
    session = session_client.session_path(project_id, session_id)
    print("Session path: {}\n".format(session))

    with open(audio_file_path, "rb") as audio_file:
        input_audio = audio_file.read()

    audio_config = dialogflow.InputAudioConfig(
        audio_encoding=audio_encoding,
        language_code=language_code,
        sample_rate_hertz=sample_rate_hertz,
    )
    query_input = dialogflow.QueryInput(audio_config=audio_config)

    request = dialogflow.DetectIntentRequest(
        session=session,
        query_input=query_input,
        input_audio=input_audio,
    )
    response = session_client.detect_intent(request=request)
    input_ = response.query_result.query_text
    output_ = response.query_result.fulfillment_text

    return input_
