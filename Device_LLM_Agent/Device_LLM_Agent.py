import os 
import re
import sys
import requests
from openai import OpenAI
import importlib
from pathlib import Path
current_dir = Path(__file__).resolve()
parent_dir = current_dir.parent.parent
sys.path.append(str(parent_dir))
import VoiceTalk_library.Client.config as config
importlib.reload(config)
import VoiceTalk_library.Client.ccm_utils as ccm_utils

os.environ['OPENAI_API_KEY'] = ""
#======================== GPT Prompt ==========================================

# All_DF_Prompt
# ./DF_Structure.csv is the organized output from All_DF_Prompt. 
All_DF_Prompt = f"""
For every Command in Google Home (e.g., BrightnessAbsolute), build a table with the following fields:
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
# ./Trait_Management.csv is the organized output from Trait_Prompt.
Trait_Prompt = """
List all Commands associated with each Trait in Google Home. For example, under the 'Brightness' Trait, list all relevant Commands like 'BrightnessAbsolute.'
"""

# Device_Type_Prompt
# ./DM_Management.csv is the organized output from Device_Type_Prompt
Device_Type_Prompt = """
List all Traits associated with each Device Type in Google Home. For example, under the ‘AC_UNIT’ Device Type, list all relevant commands like ‘FanSpeed.'
"""

# GPT Execution:
for Prompt in [All_DF_Prompt, Trait_Prompt, Device_Type_Prompt]:
    client = OpenAI()
    response_content = ""
    stream = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": Prompt}],
        stream=True,
    )
    for chunk in stream:
        if chunk.choices[0].delta.content is not None:
            response_content += chunk.choices[0].delta.content

#======================== GPT Prompt End ==========================================


# Using the CCM API to create DF(Device Feature) and DM(Device Model).
# CCM API:
ccm_utils.CCM_API_URL = config.GUI_SERVER_URL + "api/v0/"


#======================== Creating Device Feature ==========================================

# Step1: Converting the DataFrame into a list of dictionaries. [{...}, {...}, ...]
df= pd.read_csv("./DF_Structure.csv")
df['df_parameter'] = df['df_parameter'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
df = df[df['df_parameter'].apply(lambda x: x != [])]
df.index = range(len(df))
dict_rows = df.to_dict(orient="records")

# Step2: Create DFs(input & output)
for row in dict_rows:
    row['df_name'] = row['df_name']+"-O"
    ccm_utils.create_devicefeature(row)

for row in dict_rows:
    row['df_name'] = row['df_name'].rsplit("-", 1)[0]+"-I"
    row['df_type'] = "input"
    ccm_utils.create_devicefeature(row)


#======================== Creating Device Feature End ==========================================


#======================== Creating Device Model ================================================
# The following process is executed within the DM Management interface shown in Figure 3 of the paper, when the user creates the DM through drag-and-click actions.
# See SendData() function in VoiceTalk_library/Client/server.py
# The code is for developers who want to create it programmatically."

dm = pd.read_csv("./DM_Management.csv")
dm['Trait'] = dm['Trait'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
def create_dm_info(new_data):
    traitdf = pd.read_csv("./Trait_Management.csv", dtype={'Trait': 'string', 'DeviceFeature': 'string'})
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

for i in range(len(dm)):
    new_data = dm.iloc[i:i+1] 
    if new_data['Trait']!=[]:
        # Step1: Preparing data for CCM to create the DM
        dm_info = create_dm_info(new_data)
        # Step2: Create the DM
        status, res = ccm_utils.create_devicemodel(dm_info)

#======================== Creating Device Model End ================================================
