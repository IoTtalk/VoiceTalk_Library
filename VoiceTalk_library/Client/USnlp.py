import spacy
import ast
import pandas as pd
import sqlite3
import time # time measure
import os
import glob # for reading multi files
import re # for number finding
import pickle # for type quantity check
import math # for nan
#import the phrase matcher
from numerizer import numerize
from spacy.matcher import PhraseMatcher
from pint import UnitRegistry
#load a model and create nlp object
nlp = spacy.load("en_core_web_sm")
#initilize the matcher with a shared vocab
matcher = PhraseMatcher(nlp.vocab)

VoiceTalkTablePath = '../DB/VoiceTalkTable.csv'

#======= function readDB() ========
# in this function, program read files at the path "./dict/enUS/alias/"
# files data will be stored in dictionary: aliasDict
# aliasDict can be parsed by spaCy nlp()
# matcher() add the nlp() object, and give each key the match id
# no parameter, no return value is needed

def initTable():
    # read VoiceTalk table
    VoiceTalkTable = pd.read_csv(VoiceTalkTablePath)
    token_duplicated = VoiceTalkTable.duplicated().any() 
    # if(token_duplicated):
    #     print("token_duplicated", token_duplicated)
    
    list_D = VoiceTalkTable['D'].to_list()
    list_A, list_V = [],[]
    for a in VoiceTalkTable['A']:
        try:
            a_dict = ast.literal_eval(a)
            if isinstance(a_dict, dict):
                keysList = list(a_dict.keys())
                list_A.extend(keysList)
        except ValueError:
            list_A.append(a)
        except SyntaxError:
            list_A.append(a)
        
    for v in VoiceTalkTable['V']:
        try:
            v_dict = ast.literal_eval(v)
            if isinstance(v_dict, dict):
                keysList = list(v_dict.keys())
                list_V.extend(keysList)
        except ValueError:
            if(not math.isnan(v)):
                list_V.append(v)
    
    
    # print("init Table",  list_D, list_A, list_V)
    
    #obtain doc object for each word in the list and store it in a list
    D = [nlp(d) for d in list_D]
    A = [nlp(a) for a in list_A]
    V = [nlp(v) for v in list_V]


    #add the pattern to the matcher
    matcher.add("D", D)
    matcher.add("A", A)
    matcher.add("V", V)
    


    
# ============ function spellCorrection ============
# phone,van <-> fan
# number to <-> number two
# 

def spellCorrection(sentence):
    df = pd.read_csv("../DB/enUS/correction.csv")
    wrongwordlist = list(df['wrong'])
    # 新增
    wrongwordlist.sort(reverse = True, key = len)
    
    # print(wrongwordlist)
    for wrongword in wrongwordlist:
        if (wrongword in sentence):
            correctdf = df.loc[(df['wrong'] == wrongword)]
            correctword = correctdf.iloc[0]['correct']
            # 修改，使用 re.sub 修改句子，在要替換時，確認是否為邊界(r"\b" 為正則表達式的邊界)。
            # sentence = sentence.replace(str(wrongword), str(correctword))
            sentence = re.sub(r"\b" + str(wrongword) + r"\b", str(correctword), sentence)
            print("[correct process]: ", wrongword,"->", correctword)
    print("[correction]: ", sentence)
    return sentence

    
# ============  function textParse(sentence) ============
# main function, do the following:
# 1. read Database(initTable)
# 2. match the token(tokenclassifier)
# 3. detect the quantity(quantityDetect)
# 4. token & rule validation(tokenValidation)
# 5. token support check
# 6. token value check(contain Rule1Check, Rule2Check)
# sentence(string) as input parameter, return value is device_queries
    

def textParse(sentence, do_spellCorrection = True):
    sentence = sentence.lower() # lower all the chracters in sentence
    print("sentence.lower()")
    if do_spellCorrection:
        sentence = spellCorrection(sentence)
        
    initTable() # read database
    tokendict = {'D':'', 'A':'', 'V':[]}  # new a dict: token dict, default key(A/D/F/V/U) is set with empty string
    tokenlist = ['','','',''] # new a list: token,token[0~2] store D/A/V token[3] store rule/error bits, 
    device_queries = [[0]*5]*1 # init a device query(ies) which will send to devicetalk at the end of function
    
    
    # ====================   tokenclassifier start===================================
    # user matcher(doc) to classify words to tokens
    # unclassified word will be thrown away
    tokendict, tokenlist = tokenClassifier(sentence)
    # ====================   tokenclassifier end ===================================
    
    
    # ===========================  value handling start=================================
    # check if sentence contains number, before sentence redirecting
    # first remove other token D(i.e, '1' in sentence: "set fan 1 speed to 3")
    origin_sentence = sentence
    sentence = sentence.replace(tokendict['D'], "")

    
    quantity = quantityDetect(sentence)
    # print("[quantity]", quantity)
    sentence_action = tokendict['A']     # save action name before alias redirect
    sentence_device_name = tokendict['D']  # save device name before alias redirect
    sentence_value = tokendict['V']+quantity  # save device name before alias redirect
    


    # check if number of tokens is enough.
    # if not enough, token[3] will record error id    
    tokenlist[3] = tokenValidation(tokenlist,origin_sentence)

    # select Target IDF
    if(tokenlist[3] > 0):                  # if error/rule bit records rules
        IDF,tokenlist[3] = IDFSelection(tokenlist) # support check
    else:                              # if error/rule bit records errors
        print("[IDFSelection error]not enough token!") # break
    
    
    # if token has correct number and D support A, check if V is valid
    if(tokenlist[3] > 0): 
        device_queries = valueCheck(tokenlist, sentence_action, quantity, IDF) # value check and get device queries
    else: # <0 because not support
        device_queries = tokenlist

#     saveLog(sentence, tokenlist)   # save logs
    # print("[final] before send to iottalk,", "\ndevice query", device_queries)
    return  sentence_device_name, sentence_action, sentence_value, device_queries
        

    
    
    
# ======== tokenClassifer(tokendict, token) ============
# use nlp() to process sentence and matcher() to match each word to the token 
# token that cannot be matched will be thrown away
# token that can be matched will store in tokendict{, 'D', 'A', 'V'}
# token[4] will record -1 if too many tokens in a sentence
# input parameter: sentence, tokendict(empty), token(empty)
# return: tokendict, token

def tokenClassifier(sentence):
    tokendict = { 'D':'', 'A':'', 'V':[]}  # new a dict of token, default key(D/A/V) is set with empty string 
    # V is set to a list to accept multiple token
    tokenlist = ['','','',''] # new a list: token,token[0~3] store D/A/V, token[3] store rule/error bits, 
    doc = nlp(sentence)
    matches = matcher(doc)
    for match_id, start, end in matches:
        token_id = nlp.vocab.strings[match_id]  # get the token ID from matches token, i.e. 'D', 'A', 'V'
        span = doc[start:end]                   # get the object of word insentence
        # print("[token]", token_id,": " ,span.text)
        
        if(token_id == 'V'):
            # print("another V accepted")
            tokendict[token_id].append(span.text)
        elif(tokendict[token_id] == '' or tokendict[token_id] in span.text):   
            tokendict[token_id] = span.text     # insert key and value if undefined or tokendict has same value
        else:
            # print("too much element in D token!") # error message #1: too much token
            tokenlist[3] = -1
    tokenlist = [tokendict['D'], tokendict['A'], tokendict['V'], tokenlist[3]]
    return tokendict, tokenlist    



# ====== quantityDetect(sentence)
# detect if sentence exist quantity
# input: sentence (string)
# output: quantity (list)
def quantityDetect(sentence):
    quantity = []
    value_doc = nlp(sentence)
    if(len(value_doc._.numerize())>0): # if V is recognized as numeric strings, save it as a string of quantity
        quantity = list(value_doc._.numerize().values())
    return quantity


# ======= tokenValidation(token)  ========
# check if the number of token is valid
# token[3] will record rule if number of each token is enough
# token[3] will record error if number of each token is not enough
def tokenValidation(tokenlist, sentence):
    if( bool(tokenlist[0]!="")): # check if D exist
        if(tokenlist[1]!=""):                        # check if A exist
            rule = ruleLookup(tokenlist[1], sentence,tokenlist[0])          # lookup rule by A
            tokenlist[3] = rule                      # token[3] record rule
        else:
            tokenlist[3]=-3                       # error message #3: no feature found in sentence 
    else:
        tokenlist[3]=-2                           # error message #2: no device found in sentence
        
    return tokenlist[3]



# ======= ruleLookup(feature, sentence) =======
# read the Table: VoicetalkTable.csv
# look up the rule of the device feature and return rule number
# input parameter: feature(device_feature_name)
# return value: rule id, 1 for rule 1, 2 for rule 2, 0 for not found
    
def ruleLookup(action, sentence, device): #check rule by feature
    # rulelookup will read VoiceTalkTable
    # print("sentence grammar:", sentence)
    df = pd.read_csv(VoiceTalkTablePath)
    df = df[df['A'].str.contains(action)]
    rule = df.iloc[0]['Rule']
    # 新增
    if(rule == 1 and sentence.find(action) >= 0 and sentence.find(device) >= 0 and sentence.index(action) < sentence.index(device)):
        return 1
    elif(rule == 2):
        # print("rule 2 has set to")
        # 新增
        # if(sentence.find(action) >= 0 and sentence.find(device) >= 0 and sentence.find("to") >= 0 and sentence.find("set") >= 0 and sentence.index("to")>sentence.index(action)> sentence.index(device)> sentence.index('set')):
        if(sentence.find(action) >= 0 and sentence.find(device) >= 0 and sentence.find("to") >= 0 and sentence.find("set") >= 0):
            return 2
        else:
            return -6
    else:
        return -6 # grammar not match

# ======== IDFSelection(tokenlist) =====
# read VoiceTalkTable.txt, check if A exist 
# if support, return the IDF name
# if not support, record the error bit(tokenlist[4])
# input parameter: tokenlist
# return value:IDF(IDF name), tokenlist[4](error/value bit)
def IDFSelection(tokenlist):
    D = tokenlist[0]
    A = tokenlist[1]
    rule = tokenlist[3]
    # read device info in DeviceTable.txt
    VoiceTalkTable = readDeviceTable(D)
    # print("[IDFSelection]",VoiceTalkTable)
    
    if(D!=''):  #check if D supports A
        IDF = ''
        select_df = VoiceTalkTable[VoiceTalkTable['A'].str.contains(A)]
        if(len(select_df.index)!=0):
            # print("IDF to push", select_df.iloc[0]['IDF'])
            IDF = select_df.iloc[0]['IDF']
        else:
            tokenlist[3] = -4   #error message #4: Device not support such feature
            
    return IDF,tokenlist[3]


# ======== valueCheck(tokenlist, feature) ============
# input: tokenlist(list), feature(string), quantityV(string), IDF(string)
# output: device_queries(list)

def valueCheck(tokenlist, feature, quantityV,IDF): #issue give value
    D = tokenlist[0]
    A = tokenlist[1]
    stringV = tokenlist[2]
    rule = tokenlist[3]
    device_queries = [[0]*6]*1   # create a device query as return type of function

    if(rule == 1):
        if(D!= ""):
            valueV  = Rule1Check(IDF,A)
            device_queries = [D,A,valueV,rule,IDF]
        # print("[RULE1]device queries:", device_queries)
        
    elif(rule == 2):
        # 1. a number(check if exceed min/max)
        # 2. a status(transform into keyword in) 
        # 3. a quantity(check if unit support and check exceed min/max)
        if(D != ''):  #access the device info(which D and F are fitted)
            dimension = findDimension(IDF)
            paramTable = findParameter(IDF)
            select_V = paramTable.iloc[0]['V']
            # print("[RULE-2] V_Table", select_V)
            v_dict = None
            try:
                v_dict = ast.literal_eval(select_V)
            except ValueError:
                print("[ValueError]: V table not found")
            if(v_dict is not None):
                if(len(stringV)!=0):
                    if(stringV[0] in v_dict): # if exist, we dont care about the dimension(because keyword)
                        valueV = [v_dict[stringV[0]]]
                else: # if not exist in dictionary, we do care about the dimension
                    # for each quantity V, we do quantity calculation and min max check
                    # first, we check the dimension is matched
                    if(dimension != len(quantityV)+len(stringV)):
                        # print("[quantity]dimension not matched")
                        tokenlist[3] = -5
                        valueV = 0
                    else:  #iterate through all dimension
                        valueV, tokenlist = Rule2Check(IDF,quantityV, stringV, tokenlist)
            elif(v_dict is None):
                valueV, tokenlist = Rule2Check(IDF,quantityV, stringV, tokenlist)
            device_queries = [D,A,valueV,tokenlist[3],IDF]
    # print("[valueCheck end] :", "device query:",device_queries, "\n tokenlist", tokenlist)    
    return device_queries


# ====== Rule1 subfunction for valueCheck
#  input: IDF(string), token A(string)
#  output: valueV(int)

def Rule1Check(IDF,A):
    if(isinstance(IDF, str)):
        df = pd.read_csv(VoiceTalkTablePath)
        select_df = df.loc[(df['IDF']) == IDF]
        select_A = select_df.iloc[0]['A']
        try:
            a_dict = ast.literal_eval(select_A)
            if isinstance(a_dict, dict):
                valueV = [a_dict[A]]
                print("rule 1 dict find", valueV)
        except ValueError:
            print("no dictionary find")
    else:
        print("IDF is not string")
    return valueV

# ==== Rule2 function for valueCheck
# input: IDF(string), quantityV(string), stringV(string), tokenlist(list)
# output: 
def Rule2Check(IDF,quantityV, stringV, tokenlist):
    # print("===========[RULE2-Check]============")
    # print("[IDF]", IDF)
    # print("[quantityV]", quantityV)
    # print("[stringV]", stringV)
    dimension = findDimension(IDF)
    paramTable = findParameter(IDF)
    # print("[dimension]", dimension)
    value_V = []
    num_id, str_id = 0,0
    if(dimension>1):
        param_type = ast.literal_eval(paramTable.iloc[0]['Param_type'])
        param_unit = ast.literal_eval(paramTable.iloc[0]['Param_unit'])
        param_minmax = ast.literal_eval(paramTable.iloc[0]['Param_minmax'])
        # print("[multi-dimension]", param_type, param_unit, param_minmax)
    else:
        param_type = [paramTable.iloc[0]['Param_type']]
        param_unit = [paramTable.iloc[0]['Param_unit']]
        param_minmax = [paramTable.iloc[0]['Param_minmax']]
    error_flag = []
    for dim in range(dimension):
        # print("[param type] at dim",dim , ": ",param_type, type(param_type))
        if(param_type[dim] == 'string'):
            value_V.append(stringV[str_id])
            str_id= str_id+1
        else:
            # print("[type int] check unit", param_unit[dim], "on ", quantityV[num_id])
            # check if quantity need unit conversion
            if(not isPureNumber(quantityV[num_id])):
                if(param_unit[dim] != "None"):
                    # print("need unit conversion")
                    quantity = handleUnit(str(quantityV[num_id]), param_unit[dim])   # number + unit
                    if(quantity is None):
                        # print("[Unit conversion error]")
                        error_flag.append(-5) # unit conversion error

                    else:
                        # print("[Conversion OK]")
                        #check min max: IDF, device name
                        error_flag.append (checkMinMax(param_minmax, quantity._magnitude))
                        value_V.append(quantity._magnitude)
                else:
                    print("[no unit in definition]")
                    
            else:
                # print("[pure number]")
                quantity = handleValue(str(quantityV[num_id]))   # number + unit
                error_flag.append(checkMinMax(param_minmax, quantity))
                value_V.append(quantity)

            num_id = num_id+1
            # check if quantity in range min max
            
    # print("===========[END: RULE2 value-Check]============", value_V, "?")
    # #last collect 
    # print("===========[Flag check] =======================", error_flag)
    if(all(flag >0 for flag in error_flag)): #examine if one error appeared in a
        tokenlist[3] = 2
    else:
        tokenlist[3] = -5
    return value_V, tokenlist

# ====== handleValue(quantity) ========
# check if quantity contains value and number
# if quantity contains only number, return number
# if quantity contains number and value, return the result of handleUnit(quantitylist)
# input parameter: quantity(a string contains numeric values)
# return value: quantitylist[0] or handleUnit(quantitylist)
# new usage: just return value

def handleValue(quantity):
    # print("quantity: ",quantity)
    quantitylist = quantity.split(' ') # split a string into list
    
    if(len(quantitylist) == 1):
        return float(quantitylist[0])
    else:
        return handleUnit(quantitylist)

# ===== handleUnit(quantitylist) =======
# calculate the unit conversion of quantitylist
# read predefined base unit
# if number of quantitylist is even, calculate the result of unit conversion
# if number of quantitylist is 

def handleUnit(quantity, unit): # use Pint package for unit hanlding
    quantitylist = quantity.split(' ') # split a string into list
    ureg = UnitRegistry()     # new a unit module
    Q_ = ureg.Quantity        # define a quantity element quantity = (value, unit)
    
    value = 0 #init value
    if(len(quantitylist)%2 == 0):
        for q_id in range(0, len(quantitylist),2):
            try:
                value = value + Q_(int(quantitylist[q_id]), quantitylist[q_id+1]).to(unit)
            except:
                print("unit conversion error!")
                return None
        print("[base unit]:", value)
        return value
    else:
        print("Unit cannot be calculated")
        return None  # quantity error, number of value and unit mismatch

def checkMinMax(param_minmax, V):
    # print("[checkminmax]", param_minmax[0], " for ", V)
    range_minmax = ast.literal_eval(param_minmax[0])
    param_min = range_minmax[0]
    param_max = range_minmax[1]
    # print("min is ", range_minmax[0],"max is " ,range_minmax[1])
    if( (float(V) >param_max) or (float(V))<param_min):
        # print("[OUT OF Range]")
        return -5
    else:
        # print("[In Range]")
        return 2 #return 2 as rule 2



#
def findDimension(IDF):
    df = pd.read_csv(VoiceTalkTablePath)
    df = df.loc[(df['IDF'] == IDF)]
    dimension = df.iloc[0]['Param_dim']
    return dimension
    
def readDeviceTable(D):
    df = pd.read_csv(VoiceTalkTablePath)
    if(D != ""):
        df = df.loc[df['D']== D]

    return df

def findParameter(IDF):
    df = pd.read_csv(VoiceTalkTablePath)
    df = df.loc[(df['IDF'] == IDF) ]
    df = df[['IDF','V','Param_unit','Param_type', 'Param_minmax', 'Param_dim']]
    return df


def isPureNumber(quantity):
    quantitylist = quantity.split(' ') # split a string into list
    if(len(quantitylist)==1):
        return True
    else:
        return False
    

# def saveLog(sentence, tokenlist):
#     print('save log')
#     connection = sqlite3.connect("db/log.db")
#     crsr = connection.cursor()
#     # SQL command to insert the data in the table
#     sql_command = """CREATE TABLE IF NOT EXISTS log ( 
#     sentence TEXT,  
#     result CHAR(1)
#     );"""
#     crsr.execute(sql_command)

    
#     crsr.execute(f'INSERT INTO log VALUES ( "{sentence}", "{tokenlist[4]}")')

#     connection.commit()
#     connection.close()
    

# ======= aliasRedirection(tokendict, token) =============
# redirect all the alias(A/D/F/V) to deivce_model, device_name, device_feature, value_name
# input: tokendict, token
# return: token
# def aliasRedirection(tokendict, tokenlist):
#     print("No aliasRedirection for V2")           
#     tokenlist = [tokendict['D'], tokendict['A'], tokendict['V'], tokenlist[3]]
#     return tokenlist