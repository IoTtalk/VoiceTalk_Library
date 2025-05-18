import os
import sys
import re
import json
import requests
import pandas as pd
import importlib
import config
importlib.reload(config)


class LlamaAPI:
    def __init__(self):
        self.api_url = ""
    
    def main(self, method, text, project_name=None):
        self.project_name = project_name

        if method == "CG":
            self.get_field_data()  
        
        self.prompt = self.prompt_generator(method, text)
        
        raw_response = self.send_request()
        if raw_response:
            return self.extract_json_response(raw_response)
        
        return None
    
    # CG 使用
    def get_field_data(self):
        self.field_data = pd.read_csv(config.get_project_database_path(self.project_name, "enUS"))
        self.Device_List, self.Trait_List, self.DF_List = self.get_Device_List(), self.get_Trait_List(), self.get_DF_List() 
    
    # CG 使用
    def get_Device_List(self):
        return self.field_data[["DeviceName", "DeviceType"]].drop_duplicates().apply(tuple, axis=1).tolist()
    
    # CG 使用
    def get_Trait_List(self):
        return list(self.field_data['Trait'].unique())
    
    # CG 使用
    def get_DF_List(self):
        df = self.field_data.groupby('DeviceFeature').agg({
            'MappingList': 'first',  
            'DeviceType': lambda x: list(sorted(set(x)))
            }).reset_index()
        df = df.rename(columns={"MappingList":"Potential Input Value Mapping"})
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
    
    def prompt_generator(self, method, text):
        if method == "SC":
            prompt = f"""
            If there are any typos or grammatical mistakes in "{text}", correct them and provide the revised sentences.
            The JSON response would be {{"sentence": sentence}}.
            Just provide the result without any explanation.
            """
        elif method == "CG":
            prompt = f"""
            In the given request, a device-to-device model mapping can be found in the list "{self.Device_List}", a command that can be found in the list "{self.Trait_List}," and the device feature with potential input value mappings, along with the device types to which they apply, is provided in the list "{self.DF_List}."
            For example, according to the list, the string "open" should correspond to the correct input value "1".
            Please provide the best-matching device name, device type, device feature, input value pair in JSON format to handle the request.
            The JSON must align with the original meaning of the sentence and should not involve excessive inference.
            Ensure that:
            1. Verify that the InputValue in the JSON "must" be numeric.
            2. Verify that he DeviceFeature in the JSON "must" be listed in the given device feature list.
            The JSON should have the following structure: {{"DeviceName": DeviceName, "DeviceType": DeviceType, "DeviceFeature": DeviceFeature, "InputValue": InputValue}}
            Just provide the result without any explanation:"{text.lower()}"
            """
        return prompt
         
    def send_request(self):
        payload = {
            "message": self.prompt,
            "history": []
        }
        try:
            response = requests.post(self.api_url, json=payload)
            response_text = response.json()['response']
            return response_text
        except requests.RequestException as e:
            print(f"Llama Post Request failed: {e}")
            return None

    def extract_json_response(self, response_text):
        try:
            matches = re.findall(r'{[^{}]*}', response_text)
            for match in matches:
                cleaned_json = match.replace("\\n", "\n").replace("\\\\", "\\").replace("\n", "")
                try:
                    return json.loads(cleaned_json)
                except json.JSONDecodeError:
                    continue  
            print("No valid JSON object found in response.")
        except Exception as e:
            print(f"Llama Response Error parsing JSON: {e}")
        return None