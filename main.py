import os
import requests
import json
import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for, jsonify

app = Flask(__name__)

integrationKey = None
selectedDB = None
selectedRows = None
selectedProp = None
queryRes = None
databaseInfo = None

def notionOps(op, intkey, dbKey=None):

    def initConnection(intkey):
        dbKey = None
        headers = {
          "Authorization": "Bearer " + intkey,
          "Content-Type": "application/json",
          "Notion-Version": "2022-06-28",
        }

        payload = {
            "filter": {
                "property": "object",
                "value": "database",
            }
        }
    
        search_url = "https://api.notion.com/v1/search"
    
        res = requests.post(search_url, headers=headers, json=payload).json()

        for db in res["results"]:
            curTitle = db["title"][0]["plain_text"]
            dbs[curTitle] = db["id"]
            
        return dbs

    def getDbRows(intkey, dbKey):
        print("getDb triggered")

        global selectedRows
        rows = selectedRows

        headers = {
          "Authorization": "Bearer " + intkey,
          "Content-Type": "application/json",
          "Notion-Version": "2022-06-28",
        }

        payload = {
            "filter": {
                "or": [],
            }
        }

        # populating payload with submitted name property values
        for row in rows:
            row_filter = {
                "property": "Name",
                "title": {
                    "equals": row
                }
            }
            payload["filter"]["or"].append(row_filter)

        que_url = "https://api.notion.com/v1/databases/" + dbKey + "/query"

        global queryRes

        queryRes = requests.post(que_url, headers=headers, json=payload).json()
        with open("data.json", "w") as file:
            json.dump(queryRes, file, indent=4)

        db_url = "https://api.notion.com/v1/databases/" + dbKey

        res = requests.get(db_url, headers=headers).json()

        return res
    
    # def updateDb():
    #     global queryRes

    #     if queryRes == None:
    #         return jsonify({})
        
    #     for res in queryRes["results"]:
    #         rowID = res["id"]




    match op:
        case "init":
            initConnection(intkey)

        case "get":
            if dbKey:
                return getDbRows(intkey, dbKey)
            else:
                print("Error: dbkey required")
        
        # case "update":
        #     updateDb()
            

@app.route('/api', methods=('GET', 'POST'))
def api():

    global integrationKey

    if request.method == 'POST' and integrationKey == None:
        print("triggered POST and no IntKey")
        key = request.form['key']
        print("Received Key: " + key)

        if key.strip() != "":
            res = notionOps("init", key)
            print("intkey confirmed with result:", res)
            integrationKey = key
        
        return jsonify(res)

    key = integrationKey
    global selectedDB
    global selectedRows
    global selectedProp
    global databaseInfo

    if request.method == 'POST' and selectedDB == None:
        print("triggered POST and no selectedDB")
        selectedDB = request.get_json()
        db = selectedDB
        print("got selected db in api")
        print(db)

        selectedRows = db["rows"]
        res = notionOps("get", db["int"], db["db"])
        databaseInfo = res
        
        propsRes = res["properties"]
        # print(json.dumps(propsRes, indent=2))
        props = [{prop: propsRes[prop]} for prop in [p for p in propsRes][::-1]]
        # print("printing props now")
        # print(json.dumps(props, indent=2))
        return jsonify(props)
        
    elif selectedDB:
        print("triggered selectedDB but no selectedProperty")
        prop = request.get_json()
        selectedProp = prop["prop"]
        res = databaseInfo["properties"][selectedProp]
        print(res)
        return jsonify(res)
    
    return jsonify({})

@app.route('/', methods=('GET', 'POST'))
def index():

    global integrationKey
    integrationKey = None

    global selectedDB
    selectedDB = None

    global selectedRows
    selectedRows = None

    global queryRes
    queryRes = None

    global selectedProp
    selectedProp = None

    global databaseInfo
    databaseInfo = None

    return render_template('index.html')

@app.route('/file', methods=('GET', 'POST'))
def file():
    fpath = "Murano Names.xlsx"

    if not os.path.exists(fpath):
        print("no such file exists")
        return jsonify(False)
        
    fileDf = pd.read_excel(fpath)
    namesList = fileDf.iloc[0:, 0].tolist()

    return jsonify([name for name in namesList[:5] if name.strip() != ""])

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
