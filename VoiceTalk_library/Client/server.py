import os
# import sys
import pandas as pd
import json
from threading import Thread
# import time, random, requests
# import TWnlp #uncomment later
import csv
import ast

import re
import importlib
import USnlp
import config
importlib.reload(USnlp)
importlib.reload(config)

import whisper
import subprocess
import GPT_API

import time
from Dialogflow_API import detect_intent_audio
from STT_API import SpeechToText

import inflect

# 先定義要使用的 function

# device_name_to_ordinal:若有「設備+數字」情況則轉換為「序數+設備」
def device_name_to_ordinal(name):
    # 正則表達式匹配設備名稱中的數字
    match = re.search(r'(\d+)$', name)
    if match:
        # 取得數字部分並轉換為序數
        p = inflect.engine()
        number = int(match.group(1))
        ordinal = p.number_to_words(p.ordinal(number))
        # 輸出「序數+設備」
        return f"{ordinal} {name[:match.start()]}"
    else:
        # 沒有數字的設備名稱直接返回
        return name

# get_device_info : 找出所有設備的標準句資訊
def get_device_info():
    device_info = dict()
    with open(config.VoiceTalkTablePath, newline = "") as csvfile:
        # 根據 D 排序
        rows = sorted(csv.DictReader(csvfile), key=lambda row: row['D'])
        for row in rows:
            # 將 Device + number 轉換成 ordinal + device 
            device = device_name_to_ordinal(row["D"])
            info = {
                "action" : row["A"],
                "value" : [*ast.literal_eval(row["V"]).keys()],
                "rule" : row["Rule"],
            }

            if device in device_info.keys():
                device_info[device].append(info)
            else:
                device_info[device] = [info]
    print("--- get_device_info ---")
    return device_info

def generate_command_and_response(sentence, language = "en-US"):
#     if(language == 'en-US'): #English
#         name, feature,value, device_queries = USnlp.textParse(sentence) #spacy function
#     else:  # chinese
# #         name, feature,value, device_queries = TWnlp.textParse(sentence) #spacy function
#         print("chinese not yet")

    DAV_json = None
    if sentence != "":
        print("送進 GPT 的句子:", sentence)
        # 取得 GPT 回覆，DAV_json 為 dict('device', 'attribute', 'value') 或是 None
        api_gpt = GPT_API.API_GPT()
        gpt_response, DAV_json = api_gpt.main(sentence)
        print("GPT Response:", gpt_response)
        print("\n\n\nGPT JSON Output:", DAV_json)
    else:
        print("!!!***!!! empty sentance !!!***!!!")
    
    device_queries = ['', '', '', 0, '']
    if DAV_json != None:
        try:
            device_queries = check_rule_and_IDF(DAV_json)

            #get all device query(ies) from the tokenlist
            print("[ProcessSentence] is multiple device: ", isinstance(device_queries[0], list))    
            print("[ProcessSentence] how long:",len(device_queries,))
            thread = Thread(target=sendDevicetalk, args=(device_queries,))
            thread.daemon = True
            thread.start()
        except:
            device_queries[3] = -6

    # if(isinstance(device_queries[0], list) == False):
    #     returnlist = device_queries
    #     valid = device_queries[3]    # only 1 device, get valid/rule bits
    # else:
    #     for device_query in device_queries:
    #         if(device_query[3] < 0):
    #             valid = device_query[3]
    #             returnlist = device_query
    #             break
    #         else:
    #             valid = device_query[3]
    #             returnlist = device_query

    valid = device_queries[3]    # get valid/rule bits
    returnlist = device_queries  # show the success/error message of device D
    print("[valid]message bit:", valid)
    print("[response]response info:",returnlist)
    
    response = '' # init response
    # complete the response context
    if(valid < 0):
        response =  'I\'m sorry, try again.' if language == 'en-US' else '很抱歉，聽不懂請重講'
    else:
        response = 'OK, ' if language == 'en-US' else '收到，'
    print("source from response", response,"\nreturnlist:", returnlist,"\nvalid:", valid, )
    
    return {'tokenlist': returnlist, 'response': response, 'valid':valid, 'name': device_queries[0], 'feature': device_queries[1], 'value':device_queries[2]}


def check_rule_and_IDF(tokens):
    d = tokens["device"]
    a = tokens["attribute"]
    v = tokens["value"]
    rule = 0
    if d == None:
        rule = -2
    elif a == None:
        rule = -3
    elif v == None:
        rule = -5
    
    if isinstance(d, list) and len(d) > 1:
        rule = -1
    # 查詢 D/A 對應到的 IDF，若沒查到 rule = -4
    idf, rule = USnlp.IDFSelection([d, a, v, rule])

    if rule == 0:
        if a == "switch":
            rule = 1
        else:
            rule = 2

    return [d, a, v, rule, idf]


# levenshtein_distance_with_operations : 使用 levenshtein distance 演算法，計算兩個句子更改成相同的最少操作數與操作順序
def levenshtein_distance_with_operations(s1, s2):
    # 句子分詞
    words1 = s1.split()
    words2 = s2.split()

    # 建立一個二維數組，用於儲存部分編輯距離的值 (m + 1) * (n + 1)
    matrix = [[0] * (len(words2) + 1) for _ in range(len(words1) + 1)]

    # 初始化第一行和第一列，行與列都從 0 開始遞增
    for i in range(len(words1) + 1):
        matrix[i][0] = i
    for j in range(len(words2) + 1):
        matrix[0][j] = j

    # 用於儲存編輯操作的列表，儲存到當下這個位置的最小距離，以及執行操作的順序
    operations = [[[] for _ in range(len(words2) + 1)] for _ in range(len(words1) + 1)]

    # 開始填充矩陣中的其他單元格
    for i in range(1, len(words1) + 1):
        for j in range(1, len(words2) + 1):
            # 若 words1 的第 i 個字與 words2 的第 j 個字相同，cost 為 0，反之 cost = 1
            cost = 0 if words1[i - 1] == words2[j - 1] else 1
            delete_cost = matrix[i-1][j] + 1
            insert_cost = matrix[i][j-1] + 1
            replace_cost = matrix[i-1][j-1] + cost
            
            # 根據編輯操作的最小成本更新矩陣值和操作列表
            if delete_cost <= insert_cost and delete_cost <= replace_cost:
                matrix[i][j] = delete_cost
                operations[i][j] = operations[i-1][j] + [('DELETION', words1[i-1], '')]
            elif insert_cost <= delete_cost and insert_cost <= replace_cost:
                matrix[i][j] = insert_cost
                operations[i][j] = operations[i][j-1] + [('INSERTION', words2[j-1], '')]
            else:
                matrix[i][j] = replace_cost
                if cost == 1:
                    operations[i][j] = operations[i-1][j-1] + [('SUBSTITUTION', words1[i-1], words2[j-1])]
                else:
                    operations[i][j] = operations[i-1][j-1] + [('MATCH', words1[i-1], '')]

    # 最後一個單元格的值即為Levenshtein距離
    distance = matrix[len(words1)][len(words2)]
    # 最後一個單元格的操作列表即為編輯操作
    edit_operations = operations[len(words1)][len(words2)]
    return distance, edit_operations

# need_to_add_dict : 找出兩個句子是否不同，並且找出將錯誤字串替換成正確字串的詞組
# 1. token(device) 轉為代號
# 2. 跑 levenshtein_distance_with_operations 得 編輯距離 與 編輯操作說明
# 3. 以 MATCH 作為間隔，把相同間隔的 REPLACE 與 DELETE 組成一組，若有INSERTION則加入right部分
# 4. 代號 轉回 token(device)
# 5. 加入字典 (檢查要替換的字串是否為 Device 的 substring，若是的話，則不能加入字典)
def need_to_add_dict(text1, text2):
    '''
    text1: ASR辨識結果句子
    text2: 用戶手動更正後句子
    '''    
    # 將句子去除逗號和句號，並轉為小寫
    text1 = re.sub(r'[.,]', '', text1.lower()).strip()
    text2 = re.sub(r'[.,]', '', text2.lower()).strip()
    
    def get_token_list(file, col_name):
        table = pd.read_csv(file)[col_name]
        table = table.dropna()
        token_list = set()
        for key in set(table):
            if isinstance(key, str) and key.startswith("{") and key.endswith("}"):
                item_dict = ast.literal_eval(key)
                for k in item_dict.keys():
                    token_list.add(k)
            else:
                token_list.add(key)
        return list(token_list)
    
    print(text1, "-->", text2)

    # Step 1 : token 轉為代號
    # 建立TokenTable中的代號字典，D從「設備+編號」轉為「序數+設備」
    dict_D, dict_A, dict_V = {}, {}, {}
    token_D = get_token_list(config.VoiceTalkTablePath, "D")
    token_D = [device_name_to_ordinal(d) for d in token_D]
    
    token_A = get_token_list(config.VoiceTalkTablePath, "A")
    token_V = get_token_list(config.VoiceTalkTablePath, "V")

    token_list = []
    token_list.extend(token_D)
    token_list.extend(token_A)
    token_list.extend(token_V)
    token_dict = {}
    for i, key in enumerate(set(token_list), start=1):
        value = f"_token{i}_"
        token_dict[key] = value

    for key, value in token_dict.items():
        # text1 = text1.replace(key, value)
        # text2 = text2.replace(key, value)
        text1 = re.sub(r"\b" + str(key) + r"\b", str(value), text1)
        text2 = re.sub(r"\b" + str(key) + r"\b", str(value), text2)


    # Step 2 : 跑 levenshtein_distance_with_operations 得 編輯距離 與 編輯操作說明
    distance, operations = levenshtein_distance_with_operations(text1, text2)

    # Step 3 : 以 MATCH 作為間隔，把相同間隔的 REPLACE 與 DELETE 組成一組，若有INSERT則加入right部分
    operations.append(("MATCH", "", ""))
    wrong, right = "", ""
    ans_list = []
    for diff_type, change_text, add_text in operations:
#         print(diff_type, change_text, add_text)
        if diff_type == "SUBSTITUTION":
            wrong  += ' '+change_text
            right  += ' '+add_text
        elif diff_type == "DELETION":
            wrong  += ' '+change_text
        elif diff_type == "INSERTION":
            right += ' ' + change_text
        else:
            if wrong and right:
                ans_list.append((wrong.strip(), right.strip()))
                wrong, right = "", ""

    # Step 4 : 代號 轉回 token
    # trans_dict_D = {v : k for k, v in dict_D.items()}
    trans_token_dict = {v : k for k, v in token_dict.items()}
    print("ans_list:", ans_list)
    print("--------------------")
    
    added_list = []
    for t in ans_list:
        wrong = t[0]
        right = t[1]
        # Step 5 : 加入字典
        # 檢查 1. 修正前的字串不是 VoiceTalk 的 token，避免錯誤替換其他情境中的token。
        # 檢查 2. 修正後的字串是 VoiceTalk 的 token，則要檢查修正前的字串是否為 Device 的 substring，若不是的話再加入字典。
        add_flag = True
        for token in trans_token_dict.keys():
            if token in right.split(" "):
                if (len(wrong.split(" "))==1) and (any(item in trans_token_dict[token] for item in wrong.split(" "))):
                    add_flag = False
            elif (len(wrong.split(" ")) == 1) and ((token in wrong.split(" ")) or all(i.isdigit() for i in wrong.split(" "))):
                add_flag = False

        if add_flag:
            # 嘗試把代號轉回英文
            wrong = trans_token_dict.get(t[0], t[0])
            right = trans_token_dict.get(t[1], t[1])
            
            for key, value in trans_token_dict.items(): 
                wrong = re.sub(r'[.,]', '', wrong.replace(key, value)).strip()
                right = re.sub(r'[.,]', '', right.replace(key, value)).strip()
            print("加入字典:", wrong, "->", right)
            added_list.append([wrong, right])

    return added_list



# define error message format:
# 1: rule1, 2: rule2, <0: error
# -2 error: no device in sentence
# -3 error: no device feature in sentence
# -4 error: device feature need value
# -5 error: D not support F
# -6 error: sentence grammar error(order required)

#==========flask as backend=============
from flask import Flask, render_template, request, jsonify, url_for
app = Flask(__name__)

# whisper 相關參數
model = whisper.load_model("base", download_root = "./whisper_model_download")
# model = ""


#======== fast test method by sending text input=============
@app.route('/',methods=['POST','GET']) 
def index():
    device_info = get_device_info()
    return render_template("index.html", device_info = device_info) # response message add here

@app.route('/ProcessSentence', methods = ['POST','GET'])
# prcoess setence from the frontend
# input is {voice, lang_id}
def ProcessSentence():
    # 當取得 ASR 模型辨識結果後會進到這裡
    print("當取得 ASR 模型辨識結果後會進到這裡")
    print("********-----***", request.args)
    sentence = request.args.get('sentence')
    language = request.args.get('language')
    print("[voice sentence]: ", sentence) #data should be decoded from bytestrem to utf-8
    response_json = generate_command_and_response(sentence = sentence, language = language)
    
    return jsonify(response_json)

@app.route('/ManualTyping', methods=['POST'])
def ManualTyping():
    # 當使用者手動輸入後會進到這裡
    print("當使用者手動輸入後會進到這裡")
    print("********-----***", request.form)
    corrected_sentence = request.form['corrected_sentence']
    wrong_sentence = request.form['wrong_sentence']
    # after_recognition_flag 只在使用 ASR 辨識後才會是 True，可以多一層條件確保使用者是要修改 ASR 錯誤，並新增 spellCorrection 字典
    after_recognition_flag = json.loads(request.form['after_recognition_flag'].lower())
    
    # text = request.values['user']
    print("[sentence]:",corrected_sentence)
    language = 'en-US'
    language = request.form['language']

    response_json = generate_command_and_response(sentence = corrected_sentence, language = language)

    # 將 corrected_sentence 送到 USnlp 處理，若有成功控制設備再考慮是否要加入字典檔。
    if response_json["valid"] > 0 and after_recognition_flag:
        print("*-*-*-*-* 要加入字典")
        wrong_sentence = USnlp.spellCorrection(wrong_sentence)
        need_to_add_dict(text1 = wrong_sentence, text2 = corrected_sentence)

    return jsonify(response_json)

@app.route('/save', methods = ['POST','GET'])
def save():
    def saving_audio(file, path, file_name):
        # 儲存原始音檔
        org_file_path = path + "/org_file"
        os.makedirs(org_file_path, exist_ok=True)
        file.save(org_file_path + "/" + file_name)
        print("save org audio : " + org_file_path + "/" + file_name)

        # 轉換為單聲道音檔
        # output_wav =os.path.join(app.instance_path, 'DialogFlow_mono')+'/'+ str(max_index + 1) + ".wav"
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
        print("save mono audio: " + output_wav)

    # print("using_tool:", request.form.get('using_tool'))
    # print("file:", request.files.get('file'))

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
    # files.save(file_path)
    saving_audio(audio_file, uploads_dir, f_name)

    # 選擇工具進行 ASR 辨識，sentence 為最後辨識結果
    print("using tool:", request.form.get('using_tool'))
    if request.form.get('using_tool') == "Whisper":
        sentence = model.transcribe(uploads_dir + "/"+ f_name)
        sentence = sentence["text"]
        
    elif request.form.get('using_tool') == "Dialogflow":
        sentence = detect_intent_audio(config.Dia_project_id, f"{int(time.time())}", uploads_dir + "/"+ f_name, "en-US")
        
    elif request.form.get('using_tool') == "STT":
        sentence = SpeechToText(config.STT_client_file, uploads_dir + "/"+ f_name)  
    
    print("*"*30)
    print("ASR result:", sentence)
    print("*"*30)

    return {"sentence":sentence}

#sendDevicetalk should write to shared memory(command.csv)
#command csv should be very light, only contains IDF and returned Value
def sendDevicetalk(device_queries):
    # send IOT will write to shared memory
    if(isinstance(device_queries[0], list)):
        print("[F] rework:", device_queries)
        for device_query in device_queries:
            print("each query:", device_query)
            D = device_query[0]
            A = device_query[1]
            V = device_query[2]
            valid = device_query[3]
            if(valid <0):
                print("command not match IDF")
            else:
                print("command match IDF")
                IDF = device_query[4]
                df = pd.read_csv("../DB/cmd/command.csv")
                if(valid>0):
                    print("write file", V, 'type: ', type(V))
                    cmd = {'IDF':IDF, 'A':'', 'D':D, 'F':F, 'V':V}
                    df = df.append(cmd, ignore_index=True)
                    print("new df", df)
                    df.to_csv("../DB/cmd/command.csv", index=False)
    else:
        print("only 1 query", device_queries, len(device_queries))
        device_query = device_queries
        D = device_query[0]
        A = device_query[1]
        V = device_query[2]
        valid = device_query[3]
        if(valid< 0):
            print("command not match IDF")
        else:
            print("command match IDF")
            IDF = device_query[4]
            df = pd.read_csv("../DB/cmd/command.csv")
            if(valid>0):
                print("write file", V, 'type: ', type(V))
                cmd = {'IDF':IDF,  'D':D, 'A':A, 'V':V}
                # df = df.append(cmd, ignore_index=True)
                df = pd.concat([df, pd.DataFrame([cmd])], ignore_index=True)
                print("new df", df)
                df.to_csv("../DB/cmd/command.csv", index=False)

def initDB():
    # itterate through all languages
    # aggregate 2 table
    tokenTable = pd.read_csv(config.TokenTablePath)
    ruleTable = pd.read_csv(config.RuleTablePath)
    
    token_duplicated = tokenTable.duplicated(['D','A']).any() 
    if(token_duplicated):
        duplicate = tokenTable[tokenTable.duplicated(['D','A'], keep=False)]
        print("Token has duplicate value:\n", duplicate)
    else:
        list_rule, list_param_dim,list_param_unit, list_param_minmax, list_param_type = [],[],[],[],[]
        for IDF in tokenTable['IDF']:
            IDF = IDF[:-3]
            select_df = ruleTable.loc[(ruleTable['IDF'] == IDF)]
            list_rule.append( select_df.iloc[0]['Rule'])
            list_param_dim.append(select_df.iloc[0]['Param_dim'])
            list_param_type.append(select_df.iloc[0]['Param_type'])
            list_param_unit.append(select_df.iloc[0]['Param_unit'])
            list_param_minmax.append(select_df.iloc[0]['Param_minmax'])
            
            # for each IDF, search for rule Table and save
        VoiceTalkTable = tokenTable
        VoiceTalkTable['Rule'] = list_rule
        VoiceTalkTable['Param_dim'] = list_param_dim
        VoiceTalkTable['Param_type'] = list_param_type
        VoiceTalkTable['Param_unit'] = list_param_unit
        VoiceTalkTable['Param_minmax'] = list_param_minmax
        print("[OK]Init Table success", VoiceTalkTable)
        VoiceTalkTable.to_csv(config.VoiceTalkTablePath)

    return token_duplicated

def generate_token_list():
    def remove_number_suffix(device_name):
        # 用正則表達式來去掉設備名稱後的數字
        return re.sub(r'\d+$', '', device_name)
    df = pd.read_csv(config.VoiceTalkTablePath)
    
    org_col_name = ["D", "A", "Param_minmax", "V"]
    new_col_name = ["Device", "Attribute", "Range", "V_mapping"]
    df = df[org_col_name]
    df["D"] = df["D"].apply(remove_number_suffix)
    df = df.set_axis(new_col_name, axis='columns')
    df = df.drop_duplicates(subset=["Device", "Attribute"], keep="first")
    markdown_output = df.to_markdown(index=False)

    with open(config.TokenListPath, "w") as text_file:
        text_file.write(markdown_output)

if __name__ == "__main__":
    #register.registerIottalk()
    #register will be close for debug
    token_duplicated = initDB()
    
    if(token_duplicated):
        print("[Error]Init VoiceTalk Table error, System Abort")
    else:
        generate_token_list()
        app.run(host='0.0.0.0',debug=True, port=config.Port)
