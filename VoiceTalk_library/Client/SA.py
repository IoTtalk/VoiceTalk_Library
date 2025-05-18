import random
import json
import sys
import socketserver
import threading
import os
import re

ServerURL = 'https://IoTtalk Domain Name'
device_model = 'HomeAppliance_model_name' # for example: 'LIGHT'
IDF_list = ['HomeAppliance_IDF']
device_id = 'HomeAppliance_uuid'
device_name = 'HomeAppliance_name' # for example: 'first light'
exec_interval = 1  # IDF/ODF interval
socket_addr = './temp'

IDF_data_list = dict()

# 定義一個類別繼承 socketserver 的 BaseRequestHandler 類別，並覆寫 handle(self)，當收到 client 訊息時會執行 handle()。
# 若有需要初始化變數，可以覆寫 setup(self)。
# 這裡收到 voicetalk server 傳過來的 JSON 後，將要 push 的 data 放到全域變數的對應 IDF list 中。
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        global IDF_data_list
        # socket 傳輸 byte，所以收到後要先 decode 成 str
        received_data = self.request.recv(2048).decode("utf-8").strip()
        print(f"{device_name} Received data: {received_data}")

        # voicetalk 傳 {"attribute", "value"} 進來
        received_json = json.loads(received_data)
        idf = received_json["attribute"]
        data = received_json["value"]

        data_list = IDF_data_list[df_func_name(idf)]
        data_list.append(data)

        # # 看 device 收到訊息後是否需要回傳訊息給 voicetalk
        # self.request.sendall(f"{device_name} response!!!".encode("utf-8"))

# 定義一個類別同時繼承 socketserver 的 socketserver.ThreadingMixIn 與剛剛定義的 handler，此為可支援 asynchronous 的 socketserver。
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

# IDF 範例，全域變數的對應 IDF list 中取得並回傳資料，回傳 None 的話 DAN 也不會 push。
def HomeAppliance_IDF():
    global IDF_data_list
    try:
        data_list = IDF_data_list["HomeAppliance_IDF"]
        # 若 data_list 有資料就回傳，使用 pop(0) 會從 list 的頭開始拿
        if data_list:
            return data_list.pop(0)
    except:
        return None

# def Dummy_Control(data:list):
#     print(data[0])

def df_func_name(df_name):
    return re.sub(r'-', r'_', df_name)

def on_register(r):
    print(device_name, "on_register")
    global IDF_data_list
    for idf in IDF_list:
        IDF_data_list[df_func_name(idf)] = []

    # 先將 socket_addr 檔案刪除，才能再建立 socketserver 連接
    try:
        os.unlink(socket_addr)
    except OSError:
        pass
    server = ThreadedTCPServer(socket_addr, ThreadedTCPRequestHandler)
    # 執行 server.serve_forever() 開始等待 client 資料
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)