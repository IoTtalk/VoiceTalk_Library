import requests
import json

GUI_SERVER_URL = "https://classgui.iottalk.tw/"
CCM_API_URL = GUI_SERVER_URL + "api/v0/"

def create_project(project_name: str):
    response = requests.put(CCM_API_URL + 'project/', json={"p_name": project_name}).json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res
    
def get_project(project_name: str):
    response = requests.get(CCM_API_URL + 'project/' + project_name + '/').json()
    print(CCM_API_URL + 'project/' + project_name + '/')
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_project(project_id: int):
    response = requests.delete(CCM_API_URL + 'project/' + str(project_id) + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def get_devicemodel(dm: str):
    response = requests.get(CCM_API_URL + 'devicemodel/' + dm + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res
    
def get_devicemodel_list():
    response = requests.get(CCM_API_URL + f"devicemodel/").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def create_devicemodel(dm_info: str):
    # Request:
    #     {
    #         'dm_name': 'Foo',
    #         'df_list': [
    #             {
    #                 'df_id': 12,  // required
    #                 'df_parameter': [{}, ...]  // required
    #                 'tags': [],  // optional
    #             },
    #             ...
    #         ],
    #         'dm_type': 'other',  // optional
    #     }
    # Response:
    #     {
    #         'state': 'ok',
    #         'dm_id': 42,
    #     }
    # Response if name already exists with HTTP code 400:
    #     {
    #         'state': 'error',
    #         'reason': 'Device Model "..." already exists',
    #     }
    
    response = requests.put(CCM_API_URL + 'devicemodel/', json = dm_info).json()
    status = response["state"] =="ok"
    res = response["dm_id"] if status else response["reason"]
    return status, res

def create_deviceobject(project_id: int, dm_id: int, df_ids: list[int]):
    # Request:
    #     {
    #         'dm_id': 42,  // Device Model id
    #         'df': [  // list of Device Feature id
    #             123,
    #             ...
    #         ],
    #     }
    # Response:
    #     {
    #         'state': 'ok',
    #         'do_id': [42, 57]
    #     }
    # Response error if Device Model or Device Feature not found:
    #     {
    #         'state': 'error',
    #         'reason': '... not found',
    #     }
    response = requests.put(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/', json={"dm_id": dm_id, "df": df_ids}).json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def get_deviceobject(project_id: int, do_id: int):
    # 不會取得 dfo_id
    # 會列出此 dm 中所有 df，再列出有使用的 df
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/' + str(do_id) + '/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_deviceobject(project_id: int, do_id: int):
    response = requests.delete(CCM_API_URL + "project/" + str(project_id) + '/deviceobject/' + str(do_id) + '/').json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def create_networkapplication(project_id: int, input_dfo_id: int, output_dfo_id: int):
    dfo_ids = [input_dfo_id, output_dfo_id]
    status, na_list = get_networkapplication(project_id)
    n = len(na_list)
    data = {'na_name': 'Join {}'.format(n + 1), 'na_idx': n, 'dfo_ids': dfo_ids}
    response = requests.put(CCM_API_URL + "project/" + str(project_id) + '/na/', json=data).json()
    status = response["state"] =="ok"
    res = response["na_id"] if status else response["reason"]
    return status, res

def get_networkapplication(project_id: int):
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + '/na/').json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def delete_networkapplication(project_id: int, na_id: int):
    response = requests.delete(CCM_API_URL + "project/" + str(project_id) + '/na/' + str(na_id) + '/').json()
    status = response["state"] =="ok"
    res = response if status else response["reason"]
    return status, res

def get_device(project_id: int, do_id: int):
    response = requests.get(CCM_API_URL + "project/" + str(project_id) + "/deviceobject/" + str(do_id) + "/device").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def bind_device(project_id: int, do_id: int, d_id: int):
    response = requests.post(CCM_API_URL + f"project/{project_id}/deviceobject/{do_id}/device/bind/{d_id}/").json()
    status = response["state"] =="ok"
    res = response["d_name"] if status else response["reason"]
    return status, res

def unbind_device(project_id: int, do_id: int):
    response = requests.post(CCM_API_URL + f"project/{project_id}/deviceobject/{do_id}/device/unbind/").json()
    status = response["state"] =="ok"
    res = response["do_id"] if status else response["reason"]
    return status, res

def get_devicefeature(devicefeature_name: str):
    response = requests.get(CCM_API_URL + f"devicefeature/{devicefeature_name}").json()
    status = response["state"] =="ok"
    res = response["data"] if status else response["reason"]
    return status, res

def get_devicefeature_list():
    response = requests.get(CCM_API_URL + f"devicefeature/").json()
    status = response["state"] =="ok"
    res = response if status else response["reason"]
    return status, res

def create_devicefeature(df_parameters: str):
    # 'required': {
    #     'df_type': str,
    #     'df_name': str,
    #     'df_parameter': list},
    # 'optional': {
    #     'comment': str,
    #     'df_category': str,  df_category 雖然事 optional 但不給的話會失敗。
    # }
    response = requests.put(CCM_API_URL + f"devicefeature/", json=df_parameters).json()
    status = response["state"] =="ok"
    res = response["df_id"] if status else response["reason"]
    return status, res

def get_unit_list():
    response = requests.post(GUI_SERVER_URL + f"get_unit_list").json()
    return response

def get_device_list(p_id, do_id):
    payload = {
        "feature_info": json.dumps({
            "mount_info": {
                "device_feature_list": ["在 iottalk server 裡沒用到，但還是要有這個 key。詳細內容可看 iottalk-v1/lib/ccm/main.py 的 @app.route('/get_device_list')"],
                "do_id": do_id
            },
            "p_id": p_id
        })
    }
    response = requests.post(GUI_SERVER_URL + f"get_device_list", data=payload).json()
    return response
