from asyncore import read
import random
import threading
import time
import os
import ast
# from libraries.VoiceTalk_library.DB import DataBase
import pandas as pd
# database = DataBase()


class VoiceTalk:
    def __init__(self):
        self.data = 0
        print("init a daemon")
        self.thread = threading.Thread(target=self.daemon, daemon=True)
        print("init a daemon done")

    def get_random(self):
        return self.data

    def update_table(self,name, D, A, V, Language):
        if(Language == "en-US"):
            language_path = 'libraries/VoiceTalk_library/DB/enUS/TokenTable.csv'
        else:
            language_path = 'libraries/VoiceTalk_library/DB/cmnHantTW/TokenTable.csv'
        df = pd.read_csv(language_path)
        result_df = df.loc[(df['IDF'] == name)]
        if(len(result_df.index) == 0):
            print("update new table", name)
            df = df.append({'IDF':name , 'D': D, 'A': A, 'V': V}, ignore_index=True)
            df.to_csv(language_path, index=False)



    def get_data(self, name):    # read,  command  change
        # command = database.readCommand()
        # self.data = command['data']
        print("get data from certain IDF")
        df = pd.read_csv('libraries/VoiceTalk_library/DB/cmd/command.csv')
        i = df[(df.IDF == name) ].index
        print("i is:", i, type(i))
        select_df = df.loc[(df['IDF'] == name)]
        raw_data = select_df['V'].iloc[0]
        self.data = ast.literal_eval(raw_data)
        # print("select df", select_df, type(select_df))
        # print("self data: ", self.data, "!", type(self.data))
        df = df.drop(i)
        df.to_csv('libraries/VoiceTalk_library/DB/cmd/command.csv', index=False)
        return  self.data
    
    def get_info(self, name): # get infomation, should also think of valid value
        df = pd.read_csv('libraries/VoiceTalk_library/DB/cmd/command.csv')
        result_df = df.loc[(df['IDF'] == name)]
        if(len(result_df.index)!=0):
            print("get infomation for each IDF")
            A=df.loc[df['IDF'] == name, 'A'].iloc[0]
            D=df.loc[df['IDF'] == name, 'D'].iloc[0]
            F=df.loc[df['IDF'] == name, 'A'].iloc[0]
            V=df.loc[df['IDF'] == name, 'V'].iloc[0]
            Token ={'D':D, 'A':A, 'V':V}
        else:
            print("get info None")
            Token = {'D':'','A':'','V':''}
        return Token

    def set_data(self, value):
        # print("set data", self.data)
        # print("set_value",  value)
        return value

    def start(self):
        if self.thread:
            print("start daemon")
            self.thread.start()

    def stop(self):
        if self.thread:
            self.thread._stop()

    def daemon(self):
        while True:
            try:
                # a protocol to send directly to chosen IDF
                self.data = random.random()
                
                print("daemon thread")
                # Push IDF data in daemon thread
                # self.dan.push(<idf_name:str>, <data:list>)
                
                
                time.sleep(10)

            except:
                pass


