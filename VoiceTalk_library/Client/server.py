import os
import pandas as pd
import json
import csv
import ast

import re
import importlib
import config
importlib.reload(config)

import whisper
import subprocess
from Llama_API import LlamaAPI
from GPT_API import promptSC, promptCG

import time
from Dialogflow_API import detect_intent_audio
from STT_API import SpeechToText


import uuid
import re
import json
import multiprocessing
import socket
import csmapi, ccm_utils

# whisper 相關參數
model = whisper.load_model("base", download_root = "./whisper_model_download")

# Llama 相關參數
api = LlamaAPI()

# 定義一個保存 device 資訊的資料結構，讓 voicetalk 可以控制 device。
project_devices_info = dict()
# project_devices_info = {
#     "project A": {
#         "device 1": {
#             "socket_addr": ...,
#             "process": ...
#         }, ...
#     },
#     "project B": {
#         "device 1": {
#             "socket_addr": ...,
#             "process": ...
#         }, ...
#     }
# }

feature_to_trait = dict()
# feature_to_trait = {
#     "DeviceFeature1": "Trait",
#     "DeviceFeature2": "Trait",
#     ...
# }

def extract_variables_from_code(code):
    """
    使用正則表達式從 Python 程式碼中提取變數名稱及其值。
    僅適用於簡單的賦值語法，不支援函數調用或複雜表達式。
    """
    # 定義正則表達式來匹配變數賦值語句
    pattern = r"^(\w+)\s*=\s*(.+)$"  # 匹配 "變數名稱 = 值"
    variables = {}
    for line in code.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):  # 跳過空行和註解
            match = re.match(pattern, line)
            if match:
                var_name, var_value = match.groups()
                var_value = var_value.split("#")[0].strip()  # 去掉行尾註解
                # 嘗試將值轉換為適當的類型
                try:
                    parsed_value = eval(var_value, {"__builtins__": {}})
                except Exception:
                    parsed_value = var_value  # 如果轉換失敗，保留原始字串
                variables[var_name] = parsed_value
    return variables

def df_func_name(df_name):
    return re.sub(r'-', r'_', df_name)
    
# 先定義要使用的 function
def modify_template(template, device_info):
    """修改模板中的變數"""
    # 修改 IDF_list 和 ODF_list
    modified_template = template

    # 正規表達式匹配變數定義（key = value 格式）
    variable_pattern = r"^(\w+)\s*=\s*(.+)$"

    # 找出所有變數定義
    variables = re.findall(variable_pattern, modified_template, re.MULTILINE)

    # 將變數轉換成字典
    variables_dict = {var[0]: var[1].strip() for var in variables}

    ServerURL = device_info["ServerURL"]
    device_model = device_info["device_model"]
    device_name = device_info["device_name"] + "_ctl_" + device_info["project_name"]
    device_id = device_info["device_id"]
    IDF_list = [IDF['df_name'] for IDF in device_info["IDF_list"]]
    exec_interval = device_info["exec_interval"]
    socket_addr = device_info["socket_addr"]

    # 修改變數
    updated_variables = {
        "ServerURL": f"'{ServerURL}'",
        "device_model": f"'{device_model}'",
        "device_name": f"'{device_name}'",
        "device_id": f"'{device_id}'",
        "IDF_list": f"{IDF_list}",
        "exec_interval": f"{exec_interval}",
        "socket_addr": f"'{socket_addr}'",
    }

    # 更新程式碼中的變數
    for key, new_value in updated_variables.items():
        if key in variables_dict:
            # 替換變數值
            modified_template = re.sub(
                rf"^{key}\s*=\s*.+$", f"{key} = {new_value}", modified_template, flags=re.MULTILINE
            )

    # 動態生成函式部分
    idf_functions = "".join([
        f"""
def {df_func_name(idf)}():
    global IDF_data_list
    try:
        data_list = IDF_data_list["{df_func_name(idf)}"]
        if data_list:
            return data_list.pop(0)
    except KeyError:
        return None
"""
        for idf in IDF_list
    ])

    # 插入動態生成的函式，這邊是找出 HomeAppliance_IDF() 的位置並取代，但其實可以直接新增到 SA 的最後面
    pattern = r"def HomeAppliance_IDF\(\):\n(?:[ \t]+.*\n)*"
    modified_template = re.sub(pattern, idf_functions, modified_template)

    return modified_template

def execute_dai(sa_code, dai_code):
    # 執行 SA.py，取得 sa_namespace，裡面包含 SA.py 執行後的所有變數
    sa_namespace = {}
    sa_object_code = compile(sa_code, "SA.py", 'exec')
    exec(sa_object_code, sa_namespace)

    # 將 SA namespace 轉為物件，讓 DAI.py 執行時的 namespace 中也有 SA
    globals_dict = {
        "__name__": "__main__",
        "SA": type("SA", (object,), sa_namespace)
    }

    # 執行 DAI.py
    dai_object_code = compile(dai_code, "DAI.py", 'exec')
    exec(dai_object_code, globals_dict)

def load_trait_mapping(file_path):
    """
    讀取 CSV 檔案，建立 DeviceFeature 到 Trait 的對應表。
    
    :param file_path: CSV 檔案路徑
    :return: 一個字典 {DeviceFeature: Trait}
    """
    global feature_to_trait
    feature_to_trait.clear()
    
    with open(file_path, 'r') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            trait = row['Trait']
            # 將 DeviceFeature 欄位的字串解析為 Python 的列表
            device_features = eval(row['DeviceFeature'])  # 使用 eval 將字串轉換成列表
            for feature in device_features:
                feature_to_trait[feature] = trait

# get_device_info : 找出所有設備的標準句資訊
def get_device_info(project_name):
    device_info = dict()
    database_path = config.get_project_database_path(project_name, "enUS")
    if not os.path.exists(database_path):
        return None
    with open(database_path, newline = "") as csvfile:
        rows = csv.DictReader(csvfile)
        for row in rows:
            DeviceName = row["DeviceName"]
            Trait = row["Trait"]
            if DeviceName in device_info:
                device_info[DeviceName].append(Trait)
            else:
                device_info[DeviceName] = [Trait]
    # 去除重複的 Trait
    for DeviceName in device_info:
        device_info[DeviceName] = pd.unique(device_info[DeviceName]).tolist()

    return device_info

def clear_input_device(project_name):
    status, project_info = ccm_utils.get_project_by_name(project_name)
    for network_application in project_info["na"]:
        ccm_utils.delete_networkapplication(project_info["p_id"], network_application["na_id"])
    for input_device in project_info["ido"]:
        if input_device["d_id"]:
            # 若有綁定的 device 就 unbind
            ccm_utils.unbind_device(project_info["p_id"], input_device["do_id"])
        ccm_utils.delete_deviceobject(project_info["p_id"], input_device["do_id"])

def wait_for_device_registration(project_name, p_id, do_id, device_name, timeout=10, interval=0.5):
    """
    等待設備完成註冊，並返回相應的 d_id。
    """
    start_time = time.time()
    while (time.time() - start_time) < timeout:
        # 獲取設備清單
        device_list = ccm_utils.get_device_list(p_id, do_id)["device_info"]
        for d in device_list:
            if d[0] == device_name + "_ctl_" + project_name:  # 檢查是否註冊完成
                return d[2]  # 返回 d_id
        time.sleep(interval)  # 等待一段時間再重新檢查
    raise TimeoutError(f"Device '{device_name}' registration timed out.")

def check_device_and_IDF(project_name, device_name, device_feature):
    database_path = config.get_project_database_path(project_name, "enUS")
    if not os.path.exists(database_path):
        return False
    df = pd.read_csv(database_path)
    return bool(((df['DeviceName'] == device_name) & (df['DeviceFeature'] == device_feature)).any())

def connect(server_addr):
    uds_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        uds_sock.connect(server_addr)
    except socket.error as msg:
        print (msg)
    return uds_sock

def extract_number(value):
    """
    使用正則表達式處理輸入，將其轉換為純數字。
    :param value: 輸入，可以是數字或格式為 "value=數字" 的字串
    :return: 純數字，若無法處理則回傳 None
    """
    try:
        # 如果輸入是純數字，直接回傳
        if isinstance(value, (int, float)):
            return value
        
        # 如果是字串，使用正則表達式提取數字
        if isinstance(value, str):
            # 匹配字串中的數字（支援正負整數和浮點數）
            match = re.search(r"[-+]?\d*\.?\d+", value)
            if match:
                num_str = match.group()
                return float(num_str) if '.' in num_str else int(num_str)
        
        # 若無法匹配或非字串，回傳 None
        return None
    
    except (ValueError, TypeError):
        # 如果轉換失敗，回傳 None
        return None

def generate_command_and_response(sentence, language = "en-US", project_name = None):
    global api
    DAV_json = None
    if sentence != "":
        # 取得 GPT 回覆，DAV_json 為 dict('DeviceName', 'DeviceType', 'DeviceFeature', 'InputValue') 或是 None
#         cg = promptCG()
#         DAV_json = cg.main(project_name, sentence)
        
        # 取得 Llama 回覆，DAV_json 為 dict('DeviceName', 'DeviceType', 'DeviceFeature', 'InputValue')或是 None
        print("送進 LLM 的句子:", sentence)
        DAV_json = api.main("CG", sentence, project_name)

        # print("GPT Response:", gpt_response)
        print("\n\n\nGPT JSON Output:", DAV_json)
    else:
        print("empty sentance!!!")
    
    valid = -1
    DeviceName = None
    DeviceFeature = None
    Trait = None
    InputValue = None
    if DAV_json != None:
        try:
            DeviceName = DAV_json.get("DeviceName")
            DeviceFeature = DAV_json.get("DeviceFeature")
            InputValue = DAV_json.get("InputValue")
            Trait = feature_to_trait.get(DeviceFeature.split("-I")[0], "NotDefineTrait")
            if (DeviceName != None) and (DeviceFeature != None) and (InputValue != None):
                if check_device_and_IDF(project_name, DeviceName, DeviceFeature):
                    server_address = project_devices_info[project_name][DeviceName]["socket_addr"]
                    sock = connect(server_address)
                    data_json = dict()
                    try:
                        data_json["attribute"] = DeviceFeature
                        data_json["value"] = extract_number(InputValue)
                        payload = json.dumps(data_json).encode("utf-8")
                        sock.sendall(payload)
                        print(f"Send {data_json} to {DeviceName}")
                        valid = 1
                    except Exception as msg:
                        print ("msg::", msg)
                    finally:
                        sock.close()
        except:
            valid = -1

    return {'valid':valid, 'DeviceName': DeviceName, 'Trait':Trait, 'DeviceFeature': DeviceFeature, 'InputValue':extract_number(InputValue)}

#### VoiceTalk 畫面所用到的 function
# 取得 iottalk 中，同時存在於 IDF 與 ODF 中的 Device Feature
def get_dflist():
    idf_list = [idf['df_name'] for idf in ccm_utils.get_devicefeature_list()[1]["input"]]
    odf_list = [odf['df_name'] for odf in ccm_utils.get_devicefeature_list()[1]["output"]]
    idf_base = [item.replace('-I', '') for item in idf_list if '-I' in item]
    odf_base = [item.replace('-O', '') for item in odf_list if '-O' in item]
    DF_LIST = list(set(idf_base) & set(odf_base))
    return sorted(DF_LIST)
    
# 要建立 DM 的資料：dm_info
def create_dm_info(new_data):
    traitdf = pd.read_csv(config.get_trait_management_path("enUS"), dtype={'Trait': 'string', 'DeviceFeature': 'string'})
    traitdf['DeviceFeature'] = traitdf['DeviceFeature'].apply(ast.literal_eval)
    dict1 = new_data.set_index('DM')['Trait'].to_dict()
    dict2 = traitdf.set_index('Trait')['DeviceFeature'].to_dict()
    result_dict = {}

    for key, values in dict1.items():
        result_dict[key] = {subkey: dict2[subkey] for subkey in values}
    dm_name = next(iter(result_dict.keys()))

    all_values = [value for inner_dict in result_dict.values() for values in inner_dict.values() for value in values]
    dfs_list = (list(set(all_values)))

    dm_info = {
        'dm_name': dm_name,
        'df_list': []
    }

    for dfs in dfs_list:
        for suffix in ['-O', '-I']:
            df = dfs + suffix
            info = ccm_utils.get_devicefeature(df)
            dm_info['df_list'].append({
                'df_id': info[1]['df_id'],
                'df_parameter': list(info[1]['df_parameter'])
            })
    return dm_info

#========== flask as backend =============
from flask import Flask, render_template, request, jsonify, url_for, redirect
app = Flask(__name__)

# VoiceTalk Management:主畫面
@app.route('/VoiceTalkManagement',methods=['POST','GET']) 
def index_iottalk():
    iottalk_url = config.GUI_SERVER_URL
    return render_template("VT_Management.html", iottalk_url=iottalk_url)

# VoiceTalk Management:更新 Device Feature
@app.route('/UpdateDF')
def update_df():
    DF_LIST = sorted(get_dflist())
    return jsonify({"DF_list": DF_LIST})

# VoiceTalk Management:更新 Trait
@app.route('/UpdateTrait')
def update_trait():
    # Trait Managemnet 的 Trait 內容
    df = pd.read_csv(config.get_trait_management_path("enUS"), dtype={'Trait': 'string', 'DeviceFeature': 'string'})
    df_sorted = df.sort_values(by='Trait')
    Exist_Trait = df_sorted.set_index('Trait')['DeviceFeature'].to_dict()
    return jsonify(Exist_Trait=Exist_Trait)

# VoiceTalk Management:更新 DeviceModel
@app.route('/UpdateDM')
def update_DM():
    # DM Managemnet的DM
    df = pd.read_csv(config.get_dm_management_path("enUS"), dtype={'DM': 'string', 'Trait': 'string'})
    Exist_DM = df.set_index('DM')['Trait'].to_dict()
    dm_list = [dm['dm_name'] for dm in ccm_utils.get_devicemodel_list()[1]]
    # vt.iottalk全部的DM
    IoTtalk_DM = {key: "" for key in dm_list}
    return jsonify(Exist_DM=Exist_DM, IoTtalk_DM=IoTtalk_DM)

# VoiceTalk Management:接收前端送來的資料並存到 DB
# 新資料是 DM 的話：會用 CCM 在 iottalk 建立 DM
@app.route('/SendData', methods = ['POST','GET'])
def SendData():
    try:
        # DM
        if request.args.get('trait', None) is None:
            dm = request.args.get('dm')
            trait = request.args.getlist('trait[]')  # 從查詢參數中獲取 'trait'

            df = pd.read_csv(config.get_dm_management_path("enUS"), dtype={'DM': 'string', 'Trait': 'string'})
            new_data = pd.DataFrame([(dm, trait)], columns =['DM', 'Trait'])
            df = pd.concat([df, new_data], axis=0)
            df.to_csv(config.get_dm_management_path("enUS"), index=0)
            dm_info = create_dm_info(new_data)
            status, res = ccm_utils.create_devicemodel(dm_info)
            return jsonify({"dm": dm, "status": status})
        # Trait
        else:
            trait = request.args.get('trait')
            device_feature = request.args.getlist('device_feature[]')
            df = pd.read_csv(config.get_trait_management_path("enUS"), dtype={'Trait': 'string', 'DeviceFeature': 'string'})
            new_data = pd.DataFrame([(trait, device_feature)], columns =['Trait', 'DeviceFeature'])
            df = pd.concat([df, new_data], axis=0)
            df.to_csv(config.get_trait_management_path("enUS"), index=0)
            return jsonify({"trait": trait, "status": "true"})
    except:
        return jsonify({"error": "Error"}), 400  # 如果 'trait' 不存在，返回錯誤
    
@app.route('/',methods=['POST','GET']) 
def home():
    # 目前根目錄沒有事情要做，所以直接跳轉到 /VoiceTalkManagement
    return redirect(url_for('index_iottalk'))

@app.route('/SentenceCorrection', methods = ['POST','GET'])
def SentenceCorrection():
    global api
    sentence = request.args.get('sentence')
    language = request.args.get('language')
    # GPT
    # sc = promptSC()
    # corrected_sentence = sc.main(sentence)

    # Llama API 回傳為一json，取key為sentence的值，若無則回傳原句
    response_json = api.main("SC", sentence)
    corrected_sentence = response_json.get("sentence",sentence)
    
    return {'corrected_sentence': corrected_sentence}

@app.route('/ProcessSentence', methods = ['POST','GET'])
# prcoess setence from the frontend
# input is {voice, lang_id}
def ProcessSentence():
    # 當取得 ASR 模型辨識結果後會進到這裡
    print("當取得 ASR 模型辨識結果後會進到這裡")
    print("********-----***", request.args)
    sentence = request.args.get('sentence')
    language = request.args.get('language')
    project_name = request.args.get("project_name")
    print("[voice sentence]: ", sentence) #data should be decoded from bytestrem to utf-8
    response_json = generate_command_and_response(sentence = sentence, language = language, project_name = project_name)
    
    return jsonify(response_json)

@app.route('/ManualTyping', methods=['POST'])
def ManualTyping():
    # 當使用者手動輸入後會進到這裡
    print("當使用者手動輸入後會進到這裡")
    print("********-----***", request.form)
    project_name = request.form["project_name"]
    corrected_sentence = request.form['corrected_sentence']
    wrong_sentence = request.form['wrong_sentence']
    # after_recognition_flag 只在使用 ASR 辨識後才會是 True，可以多一層條件確保使用者是要修改 ASR 錯誤
    after_recognition_flag = json.loads(request.form['after_recognition_flag'].lower())

    print("corrected_sentence:", corrected_sentence)
    print("wrong_sentence:", wrong_sentence)
    print("after_recognition_flag:", after_recognition_flag)
    
    print("[sentence]:",corrected_sentence)
    language = 'en-US'
    language = request.form['language']
    response_json = generate_command_and_response(sentence = corrected_sentence, language = language, project_name = project_name)

    return jsonify(response_json)

@app.route('/save', methods = ['POST','GET'])
def save():
    def saving_audio(file, path, file_name):
        # 儲存原始音檔
        org_file_path = path + "/org_file"
        os.makedirs(org_file_path, exist_ok=True)
        file.save(org_file_path + "/" + file_name)

        # 轉換為單聲道音檔
        output_wav = path + "/" + file_name
        ffmpeg_command = [
                "ffmpeg",
                "-i", org_file_path + "/" + file_name,
                "-ac", "1",
                "-ar", "48000",
                output_wav
            ]
        # 執行 FFmpeg 命令
        subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
        
    # 儲存音檔
    uploads_dir = os.path.join(app.instance_path, 'audios')
    os.makedirs(uploads_dir, exist_ok=True)
    max_index = 0
    for root, dirs, files in os.walk(uploads_dir):
        # list comprehension
        if len(files) > 0:
            max_index = max([int(i.split(".")[0]) for i in files ]) + 1
    f_name = str(max_index) + ".wav"

    audio_file = request.files.get('file')
    saving_audio(audio_file, uploads_dir, f_name)

    # 選擇工具進行 ASR 辨識，sentence 為最後辨識結果
    print("using tool:", request.form.get('using_tool'))
    if request.form.get('using_tool') == "Whisper":
        sentence = model.transcribe(uploads_dir + "/"+ f_name)
        sentence = sentence["text"]
        
    elif request.form.get('using_tool') == "Dialogflow":
        # 載入 Dialogflow JSON 檔案
        try:
            with open(config.Dia_API_key, 'r') as f:
                Dia_project_id = json.load(f).get('project_id')
            print("Dialogflow pid:", Dia_project_id)
        except FileNotFoundError:
            print("找不到指定的 JSON 檔案")
        except json.JSONDecodeError:
            print("JSON 格式錯誤")
        except Exception as e:
            print(f"發生其他錯誤：{e}")
        sentence = detect_intent_audio(Dia_project_id, f"{int(time.time())}", uploads_dir + "/"+ f_name, "en-US")
        
    elif request.form.get('using_tool') == "STT":
        sentence = SpeechToText(config.STT_client_file, uploads_dir + "/"+ f_name)
    
    print("*"*30)
    print("ASR result:", sentence)
    print("*"*30)

    return {"sentence":sentence}

@app.route('/voicectl/<project_name>', methods = ['GET'])
def voice_control_generator(project_name):
    global project_devices_info
    global feature_to_trait
    
    # 先檢查 project 是否存在
    status, project_info = ccm_utils.get_project_by_name(project_name)
    if status == False:
        return jsonify(error=f"Project({project_name}) does not exist.")
        
    # 先清除原本 project 中的 input device，以及所有的 join function
    clear_input_device(project_name)
    # 清除 voicetalk 控制的 project devices
    device_control_info = project_devices_info.get(project_name)
    if device_control_info:
        for device in device_control_info:
            p = device_control_info[device]["process"]
            p.terminate()
        del project_devices_info[project_name]
        
    # 檢查 output device 是否存在
    if project_info["odo"] == []:
        return jsonify(error=f"There is no output device in the project({project_name}).")

    # 檢查使用的 DM 是否為 Management 頁面產生的(存在於 DB 中)
    df = pd.read_csv(config.get_dm_management_path("enUS"), dtype={'DM': 'string', 'Trait': 'string'})
    DM_set = set(df["DM"])
    invalid_DM = []
    for odo in project_info["odo"]:
        if odo["dm_name"] not in DM_set:
            invalid_DM.append(odo["dm_name"])
    if len(invalid_DM) > 0:
        return jsonify(error=f"Unrecognized DM name found: {invalid_DM}. To add or manage DM settings, please visit the /VoiceTalkManagement page.")
    
    # 1. 讀取 project 資料，取得 output device 資料。
    # 2. 根據 output device，使用 ccmapi 建立 input device。
    # 3. 自動連線。
    # 4. 產生 SA code 並註冊 input devcie 實體，device name 使用與 output device 一樣的 d_name，前面加上 voicectl_ 前墜，方便識別，socket 通訊介面名稱使用 device ID。
    # 5. Binding Device
    
    # 1. ~ 2.
    # 取得 project 資料，讀取 output device 資訊，並記錄 input device 需要資訊。
#     status, project_info = ccm_utils.get_project(project_name)
    p_id = project_info["p_id"]
    input_device_list = []
    for odo in project_info["odo"]:
        # dm_name = odo["dm_name"]
        # 紀錄 {
        # d_name ，使用在 1. 網頁提示、 2. Prompt B 的代入資訊。
        # dm_name ，使用在 1. Prompt B 的代入資訊。
        # df_list ，主要紀錄 IDF name、 comment
        # dm_id，若 IDF/ODF 共用同一個 device model，在建立 input device 時會用到。
        # dfo 的 alias_name，改名為建立 input device 時要用的 IDF。
        # }
        ido_info = dict()
        if odo["d_name"]:
            ido_info["device_name"] = odo["d_name"] # device
        else:
            return jsonify(error=f"Output device is not binding")
        ido_info["device_model"] = odo["dm_name"] # device model
        ido_info["IDF_list"] = [] # IDF
        ido_info["dm_id"] = odo["dm_id"]
        ido_info["df_ids"] = []
        for dfo in odo["dfo"]:
            feature = dfo["alias_name"].split("-O")[0]
            status, idf_info = ccm_utils.get_devicefeature(devicefeature_name = f"{feature}-I")
            ido_info["df_ids"].append(idf_info["df_id"])
            ido_info["IDF_list"].append(idf_info)
        status, do_id = ccm_utils.create_deviceobject(project_id = p_id, dm_id = ido_info["dm_id"], df_ids = ido_info["df_ids"])
        # 紀錄 do_id，在 binding 會需要用來查詢可綁定的 device list
        ido_info["do_id"] = do_id[0]
        input_device_list.append(ido_info)
        if status:
            print("建立 input device 成功:", odo["dm_name"])
        else:
            print("建立 input device 失敗:", odo["dm_name"])

    # input_device_list = [
    #     {
    #         'device_name': 'first voice_Dummy',
    #         'device_model': 'voice_dummy',
    #         'IDF_list': [{
    #             'comment': "this is DF_a-I's Description",
    #             'df_category': 'Sight',
    #             'df_id': 1162,
    #             'df_name': 'DF_a-I',
    #             'df_parameter': [{
    #                 'df_id': 1162,
    #                 'dfp_id': 4404,
    #                 'fn_id': None,
    #                 'idf_type': 'sample',
    #                 'max': 0.0,
    #                 'mf_id': None,
    #                 'min': 0.0,
    #                 'normalization': False,
    #                 'param_i': 0,
    #                 'param_type': 'int',
    #                 'u_id': None,
    #                 'unit_id': 1
    #             }],
    #             'df_type': 'input',
    #             'param_no': 1
    #         }],
    #         'dm_id': 496,
    #         'df_ids': [1162],
    #         'do_id': 'do_id'
    #     }, ...
    # ]

    # 3. 自動連線。
    status, project_info = ccm_utils.get_project_by_name(project_name)
    p_id = project_info["p_id"]

    for ido, odo in zip(project_info["ido"], project_info["odo"]):
        for input_dfo, output_dfo in zip(ido["dfo"], odo["dfo"]):
            input_dfo_id = input_dfo["dfo_id"]
            output_dfo_id = output_dfo["dfo_id"]
            status, na_id = ccm_utils.create_networkapplication(project_id = p_id, input_dfo_id = input_dfo_id, output_dfo_id = output_dfo_id)

    path = config.get_project_base_path(project_name, "enUS")
    if not os.path.exists(path):
        os.makedirs(path)
    device_control_info = dict()
    # 4. 產生並註冊 device
    for device in input_device_list:
        # 1. 讀取 SA code 並產生 SA code。
        SA_file = config.get_device_sa_path(project_name, device['device_name'], "enUS")
        # 先檢查有沒有已存在的 device SA code，若有則需要刪除。
        if os.path.exists(SA_file):
            # 讀取 SA.py
            with open(SA_file, "r", encoding="utf-8") as f:
                sa_code = f.read()
            try:
                variables = extract_variables_from_code(sa_code)
                mac_addr = variables["device_id"]
                socket_addr = variables["socket_addr"]
                # 解除註冊
                try:
                    try:
                        os.unlink(socket_addr)
                    except OSError:
                        pass
                    csmapi.deregister(mac_addr)
                except:
                    None
            except Exception as e:
                print(f"解析 {SA_file} 時發生錯誤: {e}")

        # 產生 device 的 SA code，並直接覆蓋已存在檔案。
        template_file = "SA.py"
        with open(template_file, "r", encoding="utf-8") as f:
            template_content = f.read()
        device["ServerURL"] = config.SERVER_URL #'https://class.iottalk.tw/'
        device["device_id"] = str(uuid.uuid4())
        device["exec_interval"] = 0.5
        device["socket_addr"] = config.get_device_socket_path(project_name, device['device_id'], "enUS")
        device["project_name"] = project_name
        sa_code = modify_template(template_content, device)
        with open(SA_file, "w", encoding="utf-8") as f:
            f.write(sa_code)
        # 2. 讀取 DAI code
        with open("DAI.py", "r", encoding="utf-8") as f:
            dai_code = f.read()

        p = multiprocessing.Process(target=execute_dai, args=(sa_code, dai_code), daemon=True)
        socket_and_process = dict()
        socket_and_process["socket_addr"] = device["socket_addr"]
        socket_and_process["process"] = p
        device_control_info[device['device_name']] = socket_and_process
        p.start()
    # device_control_info = {
    #     "device name": {
    #         "socket_addr": ...,
    #         "process": ...
    #     }, ...
    # }
    project_devices_info[project_name] = device_control_info

    # 5. binding
    for device in input_device_list:
        do_id = device["do_id"]
        try:
            d_id = wait_for_device_registration(project_name, p_id, do_id, device["device_name"], 5, 0.5)
            ccm_utils.bind_device(p_id, do_id, d_id)  # 綁定設備
            print(f"Device {device['device_name']} successfully bound!")
        except TimeoutError as e:
            print(e)

    # 4. 生成 voicetalk database
    # 建立 voicetalk table
    columns = ["DeviceName", "DeviceType", "Trait", "DeviceFeature", "MappingList"]
    table_data = []
    pattern = r"String='(.*?)',Value=(\d+)"
    for device in input_device_list:
        DeviceName = device["device_name"]
        DeviceType = device["device_model"]
        for feature in device["IDF_list"]:
            DeviceFeature = feature["df_name"]
            Trait = feature_to_trait.get(DeviceFeature.split("-I")[0], "NotDefineTrait")
            comment = feature["comment"]
            value_mapping_list = [(match[0], f"value={match[1]}") for match in re.findall(pattern, comment)]
            table_data.append([
                DeviceName,
                DeviceType,
                Trait,
                DeviceFeature,
                value_mapping_list
            ])
    df = pd.DataFrame(table_data, columns=columns)
    df.to_csv(config.get_project_database_path(project_name, "enUS"), index=False)

    print("project_devices_info:", project_devices_info)
    print(f"return URL: {url_for('control', project_name=project_name, _external=True, _scheme='https')}")
    # 回傳 @app.route 下方對應函數名稱為 "control" 的 route 網址
    return jsonify(url=url_for('control', project_name=project_name, _external=True, _scheme='https'))

@app.route('/control/<project_name>', methods=['GET'])
def control(project_name):
    global project_devices_info
    device_info = get_device_info(project_name)
    # 若找不到專案的 database，直接提示使用者去 iottalk project 建立。
    if device_info == None:
        return jsonify(error=f"Project({project_name}) does not exist.")

    # 檢查 device_info 中的 deivce 是否都有啟動，並嘗試重啟未啟動的 device
    try:
        device_control_info = project_devices_info.get(project_name)
        if not device_control_info:
            device_control_info = dict()
        for device in device_info:
            if device not in device_control_info:
                SA_file = config.get_device_sa_path(project_name, device, "enUS")
                if os.path.exists(SA_file):
                    # 讀取 SA.py
                    with open(SA_file, "r", encoding="utf-8") as f:
                        sa_code = f.read()
                    try:
                        variables = extract_variables_from_code(sa_code)
                        # mac_addr = variables["device_id"]
                        socket_addr = variables["socket_addr"]
                    except Exception as e:
                        print(f"解析 {SA_file} 時發生錯誤: {e}")
                # 讀取 DAI code
                with open("DAI.py", "r", encoding="utf-8") as f:
                    dai_code = f.read()
                p = multiprocessing.Process(target=execute_dai, args=(sa_code, dai_code), daemon=True)
                socket_and_process = dict()
                socket_and_process["socket_addr"] = socket_addr
                socket_and_process["process"] = p
                device_control_info[device] = socket_and_process
                p.start()
        project_devices_info[project_name] = device_control_info
    except:
        return jsonify(error=f"Device restart failed.")

    return render_template("index.html", device_info = device_info, project_name = project_name) # response message add here

if __name__ == "__main__":
    # 設定 ccm_utils 的 server url 用於發送 ccm api 的請求 (處理 iottalk project, device model, network application)
    # 設定 csmapi 的 server url 用於發送 csm api 的請求 (處理 voicetalk device register, push)
    ccm_utils.GUI_SERVER_URL = config.GUI_SERVER_URL
    ccm_utils.CCM_API_URL = config.GUI_SERVER_URL + "api/v0/"
    csmapi.ENDPOINT = config.SERVER_URL

    load_trait_mapping(config.get_trait_management_path("enUS"))

    # ================================================
    # Voice LLM Agent – Functional Route Overview
    # ================================================
    # ASR (Automatic Speech Recognition):
    #   Endpoint: /save
    #   Description: Handles audio input from the user by:
    #     - Saving the uploaded audio recording.
    #     - Performing automatic speech recognition (ASR) to transcribe the audio.

    # SC (Sentence Correction):
    #   Endpoint: /SentenceCorrection
    #   Description: Uses an LLM to correct the natural language sentence generated by ASR. 

    # CG (Command Generation):
    #   Endpoint: /ProcessSentence
    #   Location: Function generate_command_and_response (upper part: 272~284)
    #   Description: Generates an IoT control command in JSON format based on the corrected sentence.

    # Command Interpreter:
    #   Endpoint: /ProcessSentence
    #   Location: Function generate_command_and_response (lower part: 286~314)
    #   Description: Processes the generated JSON command, sends control data to the IoTtalk device via socket,
    #                and returns the execution result as a response to the user.
    # ================================================
    
    app.run(host='0.0.0.0',debug=True, port=config.Port)
