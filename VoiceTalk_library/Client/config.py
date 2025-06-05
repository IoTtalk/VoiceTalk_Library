import os

VoiceTalkDatabase = '../DB'
SERVER_URL = "https://iot.iottalk.tw/"
GUI_SERVER_URL = "https://iotgui.iottalk.tw/"

Dia_API_key = '../DB/Dialogflow_test20250507.json'
STT_client_file = "../DB/stt-20250506.json"
GPT_API_Key = ""
Llama_API_url = ""
Llama_API_key = ""

Port = 10826

def get_correction_file_path(language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, "correction.csv")

def get_trait_management_path(language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, "Trait_Management.csv")

def get_dm_management_path(language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, "DM_Management.csv")

def get_project_base_path(project_name, language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, project_name)

def get_project_database_path(project_name, language = "enUS"):
    return os.path.join(VoiceTalkDatabase, language, project_name, "VoiceTalk_database.csv")

def get_device_sa_path(project_name, device_name, language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, project_name, f"{device_name}_SA.py")

def get_device_socket_path(project_name, device_id, language="enUS"):
    return os.path.join(VoiceTalkDatabase, language, project_name, device_id)
