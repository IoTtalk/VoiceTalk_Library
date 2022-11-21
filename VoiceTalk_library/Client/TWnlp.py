import spacy
import ast
import pandas as pd
import sqlite3
import time # time measure
import os
import sys
import glob # for reading multi files
import re # for number finding
from numerizer import numerize
from spacy.matcher import PhraseMatcher
from pint import UnitRegistry
#load a model and create nlp object
nlp = spacy.load("zh_core_web_sm")
#initilize the matcher with a shared vocab
matcher = PhraseMatcher(nlp.vocab)
spellCorrectionPath = '../DB/cmnHantTW/correction/correction.txt'
# aside from english, chinese need some changes

# 1. a word segmentation before token classify(must)
from ckiptagger import data_utils, construct_dictionary, WS, POS, NER
start = time.time()
ws = WS("../../../../../data")   # word segmentation need 4 seconds
pos = POS("../../../../../data")
ner = NER("../../../../../data")

end = time.time()
print("loading time: ", end-start)
# 2. a special use of quantity managing(chosen)

#======= function readDB() ========
# in this function, program read files at the path "./dict/enUS/alias/"
# files data will be stored in dictionary: aliasDict
# aliasDict can be parsed by spaCy nlp()
# matcher() add the nlp() object, and give each key the match id
# no parameter, no return value is needed

def initTable():
    # TODO change: will read the data from VoiceTalk Table
    # a predefine rule table and a saved token table
    # the result should be 
    # Maybe no more alias
    tokenTablePath = '../DB/cmnHantTW/TokenTable.csv'
    ruleTablePath = '../DB/RuleTable.csv'
    
    # read token table
    tokenTable = pd.read_csv(tokenTablePath)
    
    list_D = tokenTable['D'].to_list()
    list_A, list_V = [],[]
    for a in tokenTable['A']:
        try:
            a_dict = ast.literal_eval(a)
            if isinstance(a_dict, dict):
                keysList = list(a_dict.keys())
                list_A.extend(keysList)
        except ValueError:
            list_A.append(a)
        except SyntaxError:
            list_A.append(a)
        
    for v in tokenTable['V']:
        try:
            v_dict = ast.literal_eval(v)
            if isinstance(v_dict, dict):
                keysList = list(v_dict.keys())
                list_V.extend(keysList)
        except ValueError:
            if(not math.isnan(v)):
                list_V.append(v)
    
    
    print("init Table", list_D, list_A, list_V)
    list_all = list_D+list_F+list_V
    #obtain doc object for each word in the list and store it in a list
    D = [nlp(d) for d in list_D]
    A = [nlp(a) for a in list_A]
    V = [nlp(v) for v in list_V]


    #add the pattern to the matcher
    matcher.add("D", D)
    matcher.add("A", A)
    matcher.add("V", V)
    
    
    
    #2nd part is aggregate 2 table
    ruleTable = pd.read_csv(ruleTablePath)
    list_rule, list_param_dim,list_param_unit, list_param_minmax, list_param_type = [],[],[],[],[]
    for IDF in tokenTable['IDF']:
        
        IDF = IDF[:-3]
        print("IDF: ", IDF)
        select_df = ruleTable.loc[(ruleTable['IDF'] == IDF)]
        print("select df:", select_df)
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
    print("initTable success", VoiceTalkTable)
    VoiceTalkTable.to_csv('../DB/VoiceTalkTable.csv')

    return list_all



# ========= chinese number redirection(word) ========
def chinese_numredirection(wordlist):
    df = pd.read_csv("dict/zhTW/num_zh.txt")
    for idx in range(len(wordlist)):
        zh_df = df.loc[(df['text1'] == wordlist[idx]) | (df['text2'] == wordlist[idx]) ]
        if(len(zh_df.index)>0):
            print("[chinese] number", wordlist[idx])
            wordlist[idx] = str(zh_df.iloc[0]['value'])
            print("number redirection", wordlist[idx])
    return wordlist

def spellCorrection(sentence):
    df = pd.read_csv("dict/zhTW/correction/correction.txt")
    wrongwordlist = list(df['wrong'])
    print(wrongwordlist)
    for wrongword in wrongwordlist:
        if (wrongword in sentence):
            correctdf = df.loc[(df['wrong'] == wrongword)]
            correctword = correctdf.iloc[0]['correct']
            sentence = sentence.replace(wrongword, correctword)
            print("[correct process]: ", wrongword,"->", correctword)
    print("[correction]: ", sentence)
    return sentence
    
    
# ============  function textParse(sentence) ============
# main function of the parsing subsystem, do the following:
# 1. read Database
# 2. match the token(tokenclassifier)
# 3. handle value
# 6. IDF selection
# 7. token value check
# sentence(string) as input parameter, return value is device_queries
    

def textParse(sentence):
    sentence = spellCorrection(sentence)
    
    alias_list_dict = initTable() # read database
    dict_for_CKIP = {}
    #store keywords in dictionary
    for alias_list in alias_list_dict:
        dict_for_CKIP.update( dict((el,1) for el in alias_list) )

    dict_for_CKIP = construct_dictionary(dict_for_CKIP)
    word_list = ws([sentence], coerce_dictionary=dict_for_CKIP) # wordlist for chinese number detection

    

    wordlist = word_list[0]
    
    tokendict = {'D':'', 'A':'', 'V':''}  # new a dict: token dict, default key(A/D/F/V/U) is set with empty string
    
    # new a list: token
    tokenlist = ['','','','',''] #token[4] store rule/error bits, 
    
    device_queries = [[0]*5]*1 # init a device query(ies) which will send to devicetalk at the end of function
    
    
    # ====================   tokenclassifier start===================================
    # user matcher(doc) to classify words to tokens
    # unclassified word will be thrown away
    # token classifier need space
    
    #user mather to tokenize
    sentence_space = ' '.join(wordlist)
    tokendict, tokenlist = tokenClassifier(sentence_space)
    # ====================   tokenclassifier end ===================================
    
    
    # ===========================  value handling start=================================
    # check if sentence contains number, before sentence redirecting
    # first remove other tokens(i.e, '1' in sentence: "set fan 1 speed to 3")
    # use the non-space version to do number detection

    sentence = sentence.replace(tokendict['D'], "")
    
    
    
# ========================== we detect the quantity =========================
# for chinese number, we use ckip entity to detect number
    
    quantity = quantityDetect(sentence , dict_for_CKIP)

    sentence_device_name = tokendict['D']
    sentence_action = tokendict['A']     # save feature name before alias redirect
    sentence_value = tokendict['V'] + quantity
    
    
    # ============================ alias redirection ================================
    # D,A,V alias should be redirect to device_model, device_name, device_feature individually
    tokenlist = aliasRedirection(tokendict, tokenlist)

    #============================ alias redirection end =================================


    # =========================== number of token validation  =======================================
    # check if number of tokens is enough.
    # if not enough, tokenlist[4] will record error id
      
    tokenlist[3] = tokenValidation(tokenlist)
    # =========================== number of token validation end =======================================    
    
    
    
    #============================ IDF selection =================================
    # if token has correct number, check if A/D support F
    if(tokenlist[3] > 0):                  # if error/rule bit records rules
        IDF, tokenlist[3] = IDFSelection(tokenlist) # support check
    else:                              # if error/rule bit records errors
        print("[error]not enough token!") # break
    
    
    #============================ Value check =================================
    # if token has correct number and A/D support F, check if V is valid
    if(tokenlist[3] > 0): 
        device_queries = valueCheck(tokenlist, sentence_feature, quantity,IDF) # value check and get device queries
    else: # <0 because not support
        device_queries = tokenlist

    saveLog(sentence, tokenlist)   # save logs
    print("[final] before send to iottalk,", "\ndevice query", device_queries)
    return sentence_device_name, sentence_feature,sentence_value, device_queries
        
# ======== tokenClassifer(tokendict, token) ============
# use matcher() to match each word to the token 
# token that cannot be matched will be thrown away
# input parameter: sentence, tokendict, token
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
        print("[token]", token_id,": " ,span.text)
        
        if(token_id == 'V'):
            print("another V accepted")
            tokendict[token_id].append(span.text)
        elif(tokendict[token_id] == '' or tokendict[token_id] in span.text):   
            tokendict[token_id] = span.text     # insert key and value in tokendict if is undefined or tokendict has same value
        else:
            print("too much element in D token!") # error message #1: too much token
            tokenlist[3] = -1
    tokenlist = [tokendict['D'], tokendict['A'], tokendict['V'], tokenlist[3]]
    return tokendict, tokenlist 
    
    
# ===== quantityDetect =========
def quantityDetect(sentence, dict_for_CKIP):
    quantity = [] 
    word_list = ws([sentence], coerce_dictionary=dict_for_CKIP) # wordlist for chinese number detection
    word_list[0] = chinese_numredirection(word_list[0])
    pos_list = pos(word_list)
    entity_list = ner(word_list, pos_list)
    # in entity list , we only find out 1. cardianl 2. quanity 3. time 4. ORDINAL
    entity_list = list(entity_list)
    for entity in entity_list[0]:
        entity = list(entity)
        if(entity[2] == 'QUANTITY' or entity[2] == 'TIME' or entity[2] == 'CARDINAL' or entity[2] == 'ORDINAL' ):
            quantity.append(handleEntity(entity[2],entity[3]))
    return quantity


# == read entity
def readEntity():
    df = pd.read_csv("dict/zhTW/entity.txt")
    return df

# == handle entity, we need to change chienese entity into english entity
# for Quantity and Time search for aliasU and redirect to english ver
# for Cardinal and Ordinal, do nothing

def handleEntity(Type, Context):
    #Context might contain number(s)+unit(s)
    #extract all units
    #change all unit to english ver
    print("[Entity Detection]", Context)
    if(Type == 'QUANTITY' or Type == 'TIME'):# get all the units in loop
        df = readEntity()
        for n in re.findall(r'[\u4e00-\u9fff]+', Context):
            # for each unit, get the absolute name
            df_abs = df.loc[((df['alias1'] == n) | (df['alias2'] == n) | (df['alias3'] == n))]
            eng_txt =df_abs.iloc[0][0]
            print(n, " to ", eng_txt)
            # change n to absolute name
            Context = Context.replace(n, " "+df_abs.iloc[0][0]+" ")
        print("[Entity change result]", Context)

    
    return Context.rstrip()
    
# === aliasRedirection(tokendict, tokenlist)

def aliasRedirection(tokendict, tokenlist):        
    tokenlist = [tokendict['A'], tokendict['D'], tokendict['F'], tokendict['V'], tokenlist[4]]
    print("[alias Redirect] Result:", tokenlist)
    return tokenlist

# ======= tokenValidation(tokenlist)  ========
# check if the number of token is valid
# token[4] will record rule if number of each token is enough
# token[4] will record error if number of each token is not enough
def tokenValidation(tokenlist):
    if(bool(tokenlist[0]!="")): # check if D exist
        if(tokenlist[1]!=""):                        # check if A exist
            rule = ruleLookup(tokenlist[2])          # lookup rule by A
            tokenlist[3] = rule                      # token[3] record rule
        else:
            tokenlist[3]=-3                       # error message #3: no feature found in sentence 
    else:
        tokenlist[3]=-2                           # error message #2: no device found in sentence
        
    return tokenlist[3]
    
# ======= ruleLookup(feature) =======
# read the Table: DevicefeatureTable.txt
# look up the rule of the device feature and return rule number
# input parameter: feature(device_feature_name)
# return: rule id, 1 for rule 1, 2 for rule 2, 0 for not found
    
def ruleLookup(action, sentence, device0): #check rule by feature
    # rulelookup will read VoiceTalkTable
    print("sentence grammar:", sentence)
    df = pd.read_csv(VoiceTalkTablePath)
    df = df[df['A'].str.contains(action)]
    rule = df.iloc[0]['Rule']
    if(rule == 1 and sentence.index(action) < sentence.index(device)):
        return 1
    elif(rule == 2):
        print("rule 2 has set to")
        if(sentence.index("to")>sentence.index(action)> sentence.index(device)> sentence.index('set')):
            return 2
        else:
            return -6
    else:
        return -6 # grammar not match

# ======== IDFSelection(tokenlist) =====
# read DeviceTable.txt, check if F exist in device_feature_list if 
# A/D match device_model/device_name
# if support, pass
# if not support, record the error bit(tokenlist[4])
# input parameter: tokenlist
# return value: tokenlist[4](error/value bit)

def IDFSelection(tokenlist):
    D = tokenlist[0]
    A = tokenlist[1]
    V = tokenlist[2]
    rule = tokenlist[3]
    # read device info in DeviceTable.txt
    VoiceTalkTable = readDeviceTable(A,D)
    print("[IDFSelection]",VoiceTalkTable )
    
    if(D!=''):  #check if D supports A
        IDF = ''
        select_df = VoiceTalkTable[VoiceTalkTable['A'].str.contains(A)]
        if(len(select_df.index)!=0):
            print("IDF to push", select_df.iloc[0]['IDF'])
            IDF = select_df.iloc[0]['IDF']
        else:
            tokenlist[3] = -4   #error message #4: Device not support such feature

            
    return IDF,tokenlist[3]


# ======== valueCheck(tokenlist, feature) ============

def valueCheck(tokenlist, feature, quantityV,IDF): #issue give value
    D = tokenlist[0]
    A = tokenlist[1]
    stringV = tokenlist[2]
    rule = tokenlist[3]
    print("that is IDF:", IDF)
    device_queries = [[0]*5]*1   # create a device query as return type of function

    
    df = pd.read_csv('../DB/VoiceTalkTable.csv')

    if(rule == 1):      #(issue): Used for value_dict in devicefaturetable.txt
        print("rule 1") #give a value for rule 1 in value_keyword list
        # for rule 1, get the value into Token V
        if(D!= ""):
            valueV  = Rule1Check(IDF,F)
            device_queries = [D,A,valueV,rule,IDF]
        print("[RULE1]device queries:", device_queries)
        
        
        
    elif(rule ==2):
        # 1. a string(do nothing and pass)
        # 2. a number(check if exceed min/max) 
        # 3. a quantity(check if unit support and check exceed min/max)
        if(D != ''):  #access the device info(which D and F are fitted)
            dimension = findDimension(IDF)
            paramTable = findParameter(IDF)
            select_V = paramTable.iloc[0]['V']
            print("[RULE-2] V_Table", select_V)
            v_dict = None
            try:
                v_dict = ast.literal_eval(select_V)
            except ValueError:
                print("[ValueError]: ")
            if(v_dict is not None):
                if(len(stringV)!=0):
                    if(stringV[0] in v_dict): # if exist, we dont care about the dimension(because keyword)
                        valueV = [v_dict[stringV[0]]]
                else: # if not exist in dictionary, we do care about the dimension
                    # for each quantity V, we do quantity calculation and min max check
                    # first, we check the dimension is matched
                    if(dimension != len(quantityV)+len(stringV)):
                        print("[quantity]dimension not matched")
                        tokenlist[4] = -5
                        valueV = 0
                    else:  #iterate through all dimension
                        valueV, tokenlist = Rule2Check(IDF,quantityV, stringV, tokenlist)
            device_queries = [A,D,F,valueV,tokenlist[4],IDF]
            # check if stringV found in

    print("[valueCheck end] :", "device query:",device_queries, "\n tokenlist", tokenlist)    
    return device_queries


# ====== Rule1 function for valueCheck
def Rule1Check(IDF,F):
    if(isinstance(IDF, str)):
        df = pd.read_csv('../DB/VoiceTalkTable.csv')
        select_df = df.loc[(df['IDF']) == IDF]
        select_F = select_df.iloc[0]['F']
        try:
            f_dict = ast.literal_eval(select_F)
            if isinstance(f_dict, dict):
                valueV = [f_dict[F]]
                print("rule 1 dict find", valueV)
        except ValueError:
            print("no dictionary find")
    else:
        print("its an A?")
    return valueV

# ==== Rule2 function for valueCheck
def Rule2Check(IDF,quantityV, stringV, tokenlist):
    print("===========[RULE2-Check]============")
    print("[IDF]", IDF)
    print("[quantityV]", quantityV)
    print("[stringV]", stringV)
    dimension = findDimension(IDF)
    paramTable = findParameter(IDF)
    print("[dimension]", dimension)
    value_V = []
    num_id, str_id = 0,0
    if(dimension>1):
        param_type = ast.literal_eval(paramTable.iloc[0]['Param_type'])
        param_unit = ast.literal_eval(paramTable.iloc[0]['Param_unit'])
        param_minmax = ast.literal_eval(paramTable.iloc[0]['Param_minmax'])
        print("[type]", param_type, param_unit, param_minmax)
    else:
        param_type = [paramTable.iloc[0]['Param_type']]
        param_unit = [paramTable.iloc[0]['Param_unit']]
        param_minmax = [paramTable.iloc[0]['Param_minmax']]
    error_flag = []
    for dim in range(dimension):
        print("[param type] at dim",dim , ": ",param_type, type(param_type))
        if(param_type[dim] == 'string'):
            value_V.append(stringV[str_id])
            str_id= str_id+1
        else:
            print("[type int] check unit", param_unit[dim], "on ", quantityV[num_id])
            # check if quantity need unit conversion
            if(not isPureNumber(quantityV[num_id])):
                if(param_unit[dim] != "None"):
                    print("need unit conversion")
                    quantity = handleUnit(str(quantityV[num_id]), param_unit[dim])   # number + unit
                    if(quantity is None):
                        print("[Unit conversion error]")
                        error_flag.append(-5) # unit conversion error

                    else:
                        print("[Conversion OK]")
                        #check min max: IDF, device name
                        error_flag.append (checkMinMax(param_minmax, quantity._magnitude))
                        value_V.append(quantity._magnitude)
                else:
                    print("[no unit in definition]")
                    
            else:
                print("[pure number]")
                quantity = handleValue(str(quantityV[num_id]))   # number + unit
                error_flag.append(checkMinMax(param_minmax, quantity))
                value_V.append(quantity)

            num_id = num_id+1
            # check if quantity in range min max
            
    print("===========[END: RULE2-Check]============", value_V, "?")
    #last collect 
    print("===========[Flag] =======================", error_flag)
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

def handleValue(quantity):
    print("quantity: ",quantity)
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
    
    #(issue)get base unit from iottalk define
    ureg.load_definitions('my_def.txt')
    ureg.default_system = 'iottalk'
    
    value = 0 #init value
    #(issue) When exception, catch the error message(wrong unit cannot be calculated. ex: 3 minute + 20 cm)
    if(len(quantitylist)%2 == 0):
        for q_id in range(0, len(quantitylist),2):
            try:
                value = value + Q_(int(quantitylist[q_id]), quantitylist[q_id+1]).to(unit)
#                 value = value + Q_(int(quantitylist[q_id]), quantitylist[q_id+1]).to_base_units()
            except:
                return None
        print("[base unit]:", value)
        return value
    else:
        print("Unit cannot be calculated")
        return None  # quantity error, number of value and unit mismatch
    
    
#followings are sub functions of value check
def checkMinMax(param_minmax, V):
    print("[checkminmax]", param_minmax[0], " for ", V)
    range_minmax = ast.literal_eval(param_minmax[0])
    param_min = range_minmax[0]
    param_max = range_minmax[1]
    print("min is ", range_minmax[0],"max is " ,range_minmax[1])
    if( (float(V) >param_max) or (float(V))<param_min):
        print("[OUT OF Range]")
        return -5
    else:
        print("[In Range]")
        return 2 #return 2 as rule 2
    
def findDimension(IDF):
    df = pd.read_csv('../DB/VoiceTalkTable.csv')
    df = df.loc[(df['IDF'] == IDF)]
    dimension = df.iloc[0]['Param_dim']
    return dimension
    


def findDeviceList(A):
    df = pd.read_csv('../DB/VoiceTalkTable.csv')
    df = df.loc[df['A'] == A]
    device_list =  list(df['D'])
    return device_list


def readDeviceTable(A,D):
    df = pd.read_csv('../DB/VoiceTalkTable.csv')
    if(D != ""):
        df = df.loc[df['D']== D]
    elif(A != ""):
        df = df.loc[df['A']== A]
    return df

def findParameter(IDF):
    df = pd.read_csv('../DB/VoiceTalkTable.csv')
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
    

