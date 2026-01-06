import os
import json
from collections import defaultdict
import re

def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(js,filepath,filename):
    if os.path.exists(filepath) == False:
        os.makedirs(filepath)
    # js=json.loads(js)
    with open(os.path.join(filepath,filename),"w", encoding="utf-8") as f:
        json.dump(js, f, ensure_ascii=False, indent=2)

name_lst=['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']

def ascii_to_char(ascii_code):
    return chr(ascii_code)

def change_name(name_dict,family_dict,name):
    if name in name_dict:
        return name_dict,family_dict,name_dict[name]
    
    if fname[name[0]]==1:
        # print("****************************",name[0])
        new_name=name[0]+'某'
    else:
        new_name=name[0]+'某'+name_lst[family_dict[name[0]]]
    name_dict[name]=new_name
    family_dict[name[0]]+=1
    return name_dict,family_dict,name_dict[name]

def find_bracket_indices(text):
    # print("-----------------",text)
    text=str(text)
    pattern = r'<(.*?)>'
    matches = re.finditer(pattern, text)
    
    # 提取每个匹配项的开始和结束下标
    indices = [(match.start(), match.end()) for match in matches]
    return indices

fname={}
names=[]

def count_family_name(content):
    indices = find_bracket_indices(content)
    # print(indices)
    for pair in indices:
        name=content[pair[0]+1:pair[1]-1]
        if name in names:
            continue
        names.append(name)
        if name[0] not in fname:
            fname.update({name[0]:1})
        else:
            fname[name[0]]+=1

def anonymize(name_dict,family_dict,content):
    indices = find_bracket_indices(content)
    # print(indices)
    new_content=content
    for pair in indices:
        # print(content[pair[0]+1:pair[1]-1])
        name_dict,family_dict,name=change_name(name_dict,family_dict,content[pair[0]+1:pair[1]-1])
        new_content=new_content.replace(content[pair[0]:pair[1]],name)
    return name_dict,family_dict,new_content
    
basic_path='../data/data_video'
files=os.listdir(basic_path)
# files=["example_"+str(i) for i in [0]]

    
for f in files:
    print(f)
    # try:
    if os.path.isdir(os.path.join(basic_path,f))==False:
        continue
    
    dict=load_json(os.path.join(basic_path,f,'data_tuned.json'))
    
    number=int(f.split("_")[-1])
    
    #证据重新编号
    for id0,lst1 in enumerate(dict["evidence"]):
        tmp=[]
        for id,content in enumerate(lst1):
            content=content.split(".")
            # if id==0 and id0==0:
            #     content.insert(0,'1')
            fl=True
            try:
                dddd=int(content[0])
            except:
                fl=False
            if fl==False:
                content.insert(0,f"{id+1}")
            else: 
                content[0]=str(id+1)
            
            new_content=""
            for i,term in enumerate(content):
                if i!=0:
                    new_content=new_content+"."
                new_content+=term
            tmp.append(new_content)
        dict["evidence"][id0]=tmp
    
    
    #匿名化
    fname.clear()
    names.clear()
    count_family_name(str(dict))
    
    name_dict=defaultdict(str)
    family_dict=defaultdict(int)
    for k,content in dict.items():
        if k=="evidence":
            continue
        name_dict,family_dict,dict[k]=anonymize(name_dict,family_dict,content)
        
    for id0,lst1 in enumerate(dict["evidence"]):
        tmp=[]
        for id,content in enumerate(lst1):
            name_dict,family_dict,new_content=anonymize(name_dict,family_dict,content)
            if new_content!="":
                tmp.append(new_content)
        dict["evidence"][id0]=tmp
        
    save_json(dict,os.path.join(basic_path,f),"data_anonymized.json")
    # except Exception as e:
    #     with open("failed_anonymity.txt", "a", encoding="utf-8") as file:
    #         file.write(str(f.split("_")[-1])+" "+str(e)+"\n")   
    continue
    
    
"""
[0,11]
"""    