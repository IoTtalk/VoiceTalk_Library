# ***[import_string]***
# ***[var_define]***
# D = Device, A = Action, V = Value
# self.D = 'device'
# self.A = 'color'
# self.V = {'red':[255,0,0], 'green':[0,255,0], 'blue':[0,0,255]}
self.D = 'device'
self.A = 'color'
self.V = {'red':[255,0,0], 'green':[0,255,0], 'blue':[0,0,255]}
# ***[init_content]***
voicetalk.update_table(type(self).__name__ ,self.D, self.A, self.V, Language)
# ***[runs_content]***
Token = voicetalk.get_info(type(self).__name__)
if( Token['D'] == self.D and Token['A'] ==self.A):
    if(Token['V'] in self.V):
        value = self.V[Token['V']]
    else:
        value = voicetalk.get_data(type(self).__name__)
    return value
else:
    return NoData