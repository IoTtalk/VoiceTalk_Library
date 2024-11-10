import os
import sys
import re
import json
import pandas as pd
from openai import OpenAI
import config

os.environ['OPENAI_API_KEY'] = ""

with open(config.TokenListPath, "r") as text_file:
    token_list = text_file.read()
# token_list = """
# | Device  | Attribute         | Range  | V_mapping                              |
# |---------|-------------------|--------|----------------------------------------|
# | light   | switch            | [0,1]  | {'turn on': 1, 'turn off': 0}          |
# | fan     | switch            | [0,1]  | {'turn on': 1, 'turn off': 0}          |
# | light   | brightness        | [0,10] | {'bright': 10, 'medium': 5, 'dark': 1} |
# | fan     | speed             | [0,10] | {'high': 10, 'medium': 5, 'low': 1}    |
# | light   | color temperature | [0,10] | {'warm': 10, 'cold': 1}                |
# | window  | switch            | [0,1]  | {'open': 1, 'close': 0}                |
# | door    | switch            | [0,1]  | {'open': 1, 'close': 0}                |
# | curtain | switch            | [0,1]  | {'open': 1, 'close': 0}                |
# """

class API_GPT():
    def __init__(self):
        self.input_text = ""
        self.output_text = ""
    def main(self, input_text):
        self.input_text = input_text
        self.input_text = self.replace_punctuation_with_space().lower()
        self.output_text = self.get_gpt_response()
        if self.output_text:
            return self.output_text, self.extract_json_response()
        return self.output_text, None

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
        The table {token_list} has three fields: Device, Attribute, and Value (including Range and V_mapping).
        Use this table to identify Device, Attribute, and Value in the following sentence: "{self.input_text}", and respond in JSON format. 
        The value must be either in the Range field or in the V_mapping field. Please first check the Range field; if there's no match, then check if the V_mapping field corresponds.
        If a sentence contains a device name preceded by an ordinal adjective like 'first,' 'second,' 'third,' etc.,then output the device name with the appended ordinal number. For example, for 'first light,' output 'light1'.
        To solve the "2" and "to" mistake, please add the following:If the sentence contains the word "set" followed by some words and the number 2, and there is no "to" between "set" and 2, replace 2 with "to".
        If there is no applicable mapping, try to find the closest matches.
        For example, for the sentence "Set the speed of the fan to 5," the corresponding entry in the table is Device=fan, Attribute=speed, and Value=5. Then the JSON response is {{"device": "fan", "attribute": "speed", "value": "5"}}.
        As another example, for the sentence “Set the speed of the fan to low,” the corresponding entry is Device=fan, Attribute=speed, and Value={{ 'high': 10, 'medium': 5, 'low': 1}}. The JSON response would be {{"device": "fan", "attribute": "speed", "value": "1"}}.
        Please explain the reasoning process.
        """
        return content

    # 從GPT回覆中取出json, 若無則回傳None
    def extract_json_response(self):
        try:
            pattern = r'json\n ?({.*?})'
            match = re.search(pattern, self.output_text, re.DOTALL)
            extracted_json_string = match.group(1)
            # Remove extra backslashes
            extracted_json_string = extracted_json_string.replace("\\n", "\n").replace("\\\\", "\\")
            return json.loads(extracted_json_string.replace("\n", ""))
        except:
            return None

if __name__ == '__main__':
    api_gpt = API_GPT()
    gpt_response, DAV_json = api_gpt.main("Turn on the first light")
    print("GPT Response:", gpt_response)
    print("\n\n\nJSON Output:", DAV_json)

