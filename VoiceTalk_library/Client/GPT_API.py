import os
import sys
import re
import json
import pandas as pd
from openai import OpenAI

import importlib
import config
importlib.reload(config)

os.environ['OPENAI_API_KEY'] = config.GPT_API_Key
class promptSC():
    def __init__(self):
        self.input_text = ""
        self.output_text = ""
    def main(self, input_text):
        self.input_text = input_text
        self.output_text = self.get_gpt_response()
        return self.extract_json_response()

    def get_gpt_response(self):
        content = self.create_prompt()
        client = OpenAI()
        response_content = ""
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                response_content += chunk.choices[0].delta.content

        return response_content

    def create_prompt(self):
        content = f"""
        If there are any typos or grammatical mistakes in "{self.input_text}", correct them and provide the revised sentences in json format, where the JSON key is "sentence".
        """
        return content
    # 從GPT回覆中取出json, 若無則回傳原始句
    def extract_json_response(self):
        try:
            pattern = r'json\n?({.*?})'
            match = re.search(pattern, self.output_text, re.DOTALL)
            if match:
                cleaned_json = match.group(1).replace("\\n", "\n").replace("\\\\", "\\").replace("\n", "")
                return json.loads(cleaned_json).get('sentence', self.input_text)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing JSON: {e}")
        return self.input_text

    
class promptCG():
    def __init__(self):
        # 場域名稱
        self.input_text = ""
        self.output_text = ""
    def main(self, project_name, input_text):
        
        # 根據場域名稱(field_name)產生所需list
        self.field_data = pd.read_csv(config.get_project_database_path(project_name, "enUS"))
        self.Device_List, self.Trait_List, self.DF_List = self.get_Device_List(), self.get_Trait_List(), self.get_DF_List()
        
        # input_text: 先去除標點符號和轉為小寫
        self.input_text = input_text
        self.input_text = self.replace_punctuation_with_space().lower()
        
        # GPT輸出結果，並取出json format        
        self.output_text = self.get_gpt_response()
        return self.extract_json_response()
    
    def get_Device_List(self):
        return self.field_data[["DeviceName", "DeviceType"]].drop_duplicates().apply(tuple, axis=1).tolist()
    
    def get_Trait_List(self):
        return list(self.field_data['Trait'].unique())
    
    def get_DF_List(self):
        df = self.field_data[["DeviceFeature", "MappingList"]].drop_duplicates()
        header = "| " + " | ".join(df.columns) + " |"
        separator = "| " + " | ".join(['-' * len(col) for col in df.columns]) + " |"    
        # 表內容
        rows = [
            "| " + " | ".join(str(value).ljust(len(col)) for value, col in zip(row, df.columns)) + " |"
            for row in df.values
        ]    
        # 合併
        markdown_table = "\n".join([header, separator] + rows)
        return markdown_table

    # 使用正則表達式匹配標點符號，但保留撇號
    def replace_punctuation_with_space(self):
        return re.sub(r"[^\w\s']", ' ', self.input_text).replace("  ", " ")
    
    def get_gpt_response(self):
        content = self.create_prompt()
        client = OpenAI()
        response_content = ""
        stream = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                response_content += chunk.choices[0].delta.content

        return response_content

    def create_prompt(self):
        content = f"""
        n the following request, a device-to-device model mapping can be found in the list "{self.Device_List}," a command is available in the list "{self.Trait_List}," and the device feature and potential input value mapping is provided in the list "{self.DF_List}".
Please list the device name, device type, and the (device feature, input value) pair in JSON format that best handles the following request.
The JSON should follow this structure:
{{"DeviceName": "devicename", "DeviceType": "devicetype", "DeviceFeature": "devicefeature", "InputValue": "inputvalue"}}
Input values should preferably be numeric, but they do not necessarily have to be from the mapping list.
Just provide the results without any explanation or comment: "{self.input_text}"
        """
        return content

    # 從GPT回覆中取出json, 若無則回傳None
    def extract_json_response(self):
        try:
            pattern = r'({.*?})'
            match = re.search(pattern, self.output_text, re.DOTALL)
            if match:
                cleaned_json = match.group(1).replace("\\n", "\n").replace("\\\\", "\\").replace("\n", "")
                return json.loads(cleaned_json)
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error parsing JSON: {e}")
        return None