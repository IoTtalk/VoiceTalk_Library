import json, sys, socketserver, threading, os, re

ServerURL = '<https://IoTtalk_server_domain_name>'
device_model = '<HomeAppliance_model_name>' # for example: 'LIGHT'
IDF_list = ['<HomeAppliance_IDF>']
device_id = '<HomeAppliance_uuid>'
device_name = '<HomeAppliance_name>' # for example: 'first light'
exec_interval = 1  # IDF execution interval
socket_addr = './temp'

IDF_data_list = dict()

# Define a class that inherits from `socketserver.BaseRequestHandler and override the `handle(self)` method. The `handle()` method will be executed when a message is received from a client.
# If there is a need to initialize variables, you can override the `setup(self)` method.
# After receiving the JSON sent from the voicetalk server, extract the data to be pushed and place it into the corresponding IDF list in the global variable.
class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        global IDF_data_list
        # Since socket transmission uses bytes, the received data must first be decoded into a string.
        received_data = self.request.recv(2048).decode("utf-8").strip()
        print(f"{device_name} Received data: {received_data}")

        # Voicetalk sends data in the format `{"attribute", "value"}`.
        received_json = json.loads(received_data)
        idf = received_json["attribute"]
        data = received_json["value"]

        data_list = IDF_data_list[df_func_name(idf)]
        data_list.append(data)

        # Depending on the device, determine whether you need to send a response back to voicetalk after receiving a message.
        # self.request.sendall(f"{device_name} response!!!".encode("utf-8"))

# Define a class that inherits from both `socketserver.ThreadingMixIn` and the previously defined handler class. This creates a socket server that supports asynchronous (multithreaded) handling.
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    allow_reuse_address = True

# IDF example: Retrieve and return data from the corresponding IDF list in the global variable. If `None` is returned, DAN will not push the data.
def HomeAppliance_IDF():
    global IDF_data_list
    try:
        data_list = IDF_data_list["HomeAppliance_IDF"]
        # If `data_list` contains data, return it using `pop(0)`, which retrieves and removes the first element from the list.
        if data_list:
            return data_list.pop(0)
    except:
        return None

def df_func_name(df_name):
    return re.sub(r'-', r'_', df_name)

def on_register(r):
    print(device_name, "on_register")
    global IDF_data_list
    for idf in IDF_list:
        IDF_data_list[df_func_name(idf)] = []

    # Delete the `socket_addr` file first before creating the socket server connection again.
    try:
        os.unlink(socket_addr)
    except OSError:
        pass
    server = ThreadedTCPServer(socket_addr, ThreadedTCPRequestHandler)
    # Call `server.serve_forever()` to start waiting for client data.
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
