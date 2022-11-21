import os
import sys
import pandas as pd
import json
from threading import Thread
import time, random, requests
# import TWnlp #uncomment later
import USnlp
import config




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


#======== fast test method by sending text input=============
@app.route('/',methods=['POST','GET']) 
def index():
    returnlist = []
    tokenlist = ['','','','',-1]
    response = ''
    if(request.method == 'POST'):
        text = request.values['user']
        print("[sentence]:",text)
        language = 'en-US'
        # use text to send for demo
        # add rule to check if chinese or english
        if(language == 'en-US'): #English
            #enspacy.readDB()
            name, feature,value, device_queries = USnlp.textParse(text) #spacy function
        else:  # chinese
            name, feature,value, device_queries = TWnlp.textParse(text) #spacy function
            print("chinese not yet")
        
        
        #get all device query(ies) from the tokenlist
        print("[ProcessSentence] is multiple device: ", isinstance(device_queries[0], list))
        
        
        print("[IOTTALK V2]", device_queries)
        thread = Thread(target=sendDevicetalk, args=(device_queries,))
        thread.daemon = True
        thread.start()
        
        
        
        if(isinstance(device_queries[0], list) == False):
            returnlist = device_queries
            valid = device_queries[3]    # only 1 device, get valid/rule bits
        else:
            for device_query in device_queries:
                if(device_query[3] < 0):
                    valid = device_query[3]
                    returnlist = device_query
                    break
                else:
                    valid = device_query[3]
                    returnlist = device_query
        
        print("[valid]message bit:", valid)
        print("[response]response info:",returnlist)
        response = ''
        if(valid < 0):
            response =  'I\'m sorry, try again.' if language == 'en-US' else '很抱歉，聽不懂請重講'
            returnlist = []
        else:
            response = 'OK, ' if language == 'en-US' else '收到，'
            #returnlist[2] = feature
            #if(returnlist[4] == 1): returnlist[3] = ''

    return render_template("index.html",returnlist=returnlist, response = response) # response message add here


@app.route('/ProcessSentence', methods = ['POST','GET'])
# prcoess setence from the frontend
# input is {voice, lang_id}
def ProcessSentence():
    returnlist = []
    sentence = request.args.get('sentence')
    language = request.args.get('language')
    print("[voice sentence]: ", sentence) #data should be decoded from bytestrem to utf-8
    
    if(language == 'en-US'): #English
        name, feature,value, device_queries = USnlp.textParse(sentence) #spacy function
    else:  # chinese
#         name, feature,value, device_queries = TWnlp.textParse(sentence) #spacy function
        print("chinese not yet")
    
    #get all device query(ies) from the tokenlist
    #get all device query(ies) from the tokenlist
    print("[ProcessSentence] is multiple device: ", isinstance(device_queries[0], list))    
    print("[ProcessSentence] how long:",len(device_queries,))
    thread = Thread(target=sendDevicetalk, args=(device_queries,))
    thread.daemon = True
    thread.start()

    valid = device_queries[3]    # get valid/rule bits
    returnlist = device_queries  # show the success/error message of device D
    
    response = '' # init response
    # complete the response context
    if(valid < 0):
        response =  'I\'m sorry, try again.' if language == 'en-US' else '很抱歉，聽不懂請重講'
    else:
        response = 'OK, ' if language == 'en-US' else '收到，'
            
    print("source from response", response,"\nreturnlist:", returnlist,"\nvalid:", valid, )
    
    
    return jsonify({ 'tokenlist': returnlist, 'response': response, 'valid':valid, 'name': name, 'feature': feature, 'value':value})



#sendDevicetalk should write to shared memory(command.csv)
#command csv should be very light, only contains IDF and returned Value
def sendDevicetalk(device_queries):
    # senf IOT will write to shared memory
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
                df = df.append(cmd, ignore_index=True)
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
    

if __name__ == "__main__":
    #register.registerIottalk()
    #register will be close for debug
    token_duplicated = initDB()
        
    if(token_duplicated):
        print("[Error]Init VoiceTalk Table error, System Abort")
    else:
        app.run(host='0.0.0.0',debug=True, port=config.Port)
    