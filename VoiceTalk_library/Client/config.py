import os

# TokenTablePath = '../DB/enUS/TokenTable.csv'
# RuleTablePath = '../DB/RuleTable.csv'
# VoiceTalkTablePath = '../DB/VoiceTalkTable.csv'
# TokenListPath = '../DB/TokenList.txt'

VoiceTalkDatabase = '../DB'
# SERVER_URL = "https://class.iottalk.tw/"
# GUI_SERVER_URL = "https://classgui.iottalk.tw/"
SERVER_URL = "https://vt.iottalk.tw/"
GUI_SERVER_URL = "http://vt.iottalk.tw:7788/"

Dia_API_key = '../DB/Dialogflow_test1.json'
Dia_project_id = "test1-cidr"
STT_client_file = "../DB/stt-demo20241130"

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
