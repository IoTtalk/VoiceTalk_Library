#!/usr/bin/env python
# coding: utf-8


import os
import sys
import re
import json
from openai import OpenAI

os.environ['OPENAI_API_KEY'] = ""

# DF_Prompt
# "Command" appears in the "df_name" column of ./DF_Structure.csv, which is the organized output from DF_Prompt. 
# Among the 69 commands, 19 do not have parameters, so only 50 Device Features were built.
DF_Prompt = f"""
For the "{command}" Command in Google Home, build a table with the following fields:
1.DF Name: Fill in the Command name (e.g., BrightnessAbsolute).
2.Number of Parameters: Enter the total number of parameters for the Command.
3.For each parameter (i-th parameter), include the following fields:
    •X-i: Fill with the parameter name (e.g., X1 for the first parameter, X2 for the second parameter, etc.).
    •Data Type: Specify the type of the parameter (e.g., integer, float, etc.).
    •Min: Enter the minimum value of the parameter. If no default minimum value is provided, and there is one default value, enter the default value here.
    •Max: Enter the maximum value of the parameter. If no default maximum value is provided, and there is one default value, enter the default value here. Otherwise, fill in nil.
    •Unit: Specify the unit of the parameter (if applicable).
4.Comment: Include any additional information about the Command. For example, if the Command defines string labels with values, for every string “s” with value “v”, list it as “String=s, Value=v”.
"""

# Trait_Prompt
# ./Trait_Management.csv is the organized output from Trait_Prompt
Trait_Prompt = f"""
List all Commands associated with each Trait in Google Home. For example, under the 'Brightness' Trait, list all relevant Commands like 'BrightnessAbsolute.'
"""

# Device_Type_Prompt
# ./DM_Management.csv is the organized output from Device_Type_Prompt
Device_Type_Prompt = f"""
List all Traits associated with each Device Type in Google Home. For example, under the ‘AC_UNIT’ Device Type, list all relevant commands like ‘FanSpeed.'
"""

# Execution 
client = OpenAI()
response_content = ""
stream = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": DF_Prompt}], # DF_Prompt, Trait_Prompt or Device_Type_Prompt
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content is not None:
        response_content += chunk.choices[0].delta.content
print(response_content)


# Creating DF
# converting the DataFrame into a list of dictionaries.
# The Device Feature is created in IoTTalk using the CCM API with a list of dictionaries.
# CCM API:
import requests
CCM_API_URL = "http://vt.iottalk.tw:7788/api/v0/"
def create_devicefeature(df_parameters: str):
    # 'required': {
    #     'df_type': str,
    #     'df_name': str,
    #     'df_parameter': list},
    # 'optional': {
    #     'comment': str,
    #     'df_category': str, 
    # }
    response = requests.put(CCM_API_URL + f"devicefeature/", json=df_parameters).json()
    status = response["state"] =="ok"
    res = response["df_id"] if status else response["reason"]
    return status, res

df = pd.read_csv("./DF_Structure.csv")
df = df.drop(columns=['Trait'])
df['df_parameter'] = df['df_parameter'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
df = df[df['df_parameter'].apply(lambda x: x != [])]
df.index = range(len(df))
dict_rows = df.to_dict(orient="records")

for newdf in dict_rows:
    try:
        newdf['df_type'] = "input"
        newdf['df_name'] = newdf['df_name']+"-I"
        create_devicefeature(newdf)
