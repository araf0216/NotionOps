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
toUpdate = None
hasUpdated = False

def notionOps(op, intkey, dbKey=None):

    def initConnection(intkey):
        dbKey = None
        dbs = {}
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

        print(dbs)
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

        # for logging the pre-update state of data retrieved
        with open("data.json", "w") as file:
            json.dump(queryRes, file, indent=4)

        db_url = "https://api.notion.com/v1/databases/" + dbKey

        res = requests.get(db_url, headers=headers).json()

        return res
    
    def updateDb():
        print("update action triggered")

        global queryRes
        global selectedProp
        global toUpdate


        if queryRes == None or toUpdate == None or selectedProp == None:
            return jsonify("failed")
        
        namesList = None
        # if toUpdate == "date":
        #     fpath = "Murano Names.xlsx"

        #     fileDf = pd.read_excel(fpath)
        #     namesList = fileDf.iloc[:, 1].tolist()

        #     namesList = [name for name in namesList[:5] if name.strip() != ""]

        # queryRes contains the necessary rows and their page id's
        for res in queryRes["results"]:
            pageID = res["id"]

            rowUrl = "https://api.notion.com/v1/pages/" + pageID

            headers = {
                "Authorization": "Bearer " + intkey,
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }


            match toUpdate:
                case "checked":
                    val = True
                case "unchecked":
                    val = False
                # case "date":
                #     val = namesList[res["properties"]["Name"]["title"]["text"]["content"]]
                #     print("Date change to:", val)

            properties = {
                "properties": {
                    selectedProp: val,
                }
            }
            print("triggered db PATCH itself with:", properties)

            res = requests.patch(rowUrl, headers=headers, json=properties).json()


            if res == {}:
                print(res)
                return "failed"
            
            if res["object"] == "error":
                print(res)
                return "failed"
        
        return "success"




    match op:
        case "init":
            return initConnection(intkey)

        case "get":
            if dbKey:
                return getDbRows(intkey, dbKey)
            else:
                print("Error: dbkey required")
        
        case "update":
            return updateDb()
            

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
    global toUpdate

    if request.method == 'POST' and selectedDB == None:
        print("triggered submission of database AND rows selections")
        selectedDB = request.get_json()
        db = selectedDB
        print("got selected db in api")
        print(db)

        selectedRows = db["rows"]
        res = notionOps("get", db["int"], db["db"])
        databaseInfo = res
        
        propsRes = res["properties"]
        props = [{prop: propsRes[prop]} for prop in [p for p in propsRes][::-1]]
        return jsonify(props)
        
    elif selectedDB and selectedProp == None:
        print("triggered property submission")
        prop = request.get_json()
        selectedProp = prop["prop"]
        res = databaseInfo["properties"][selectedProp]
        print(res)
        print("selected prop", selectedProp)
        # selectedProp = None
        return jsonify(res)
    
    elif selectedProp:
        print("triggered update")
        # use selectedProp to take in input as to new value to update the selected property to
        print("Selected property to update", selectedProp)
        #perform the actual update
        value = request.get_json()
        
        toUpdate = value["value"]
        print("Selected update to the property", value["value"])

        res = notionOps("update", key)

        # #clear the selected prop
        # selectedProp = None
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
    namesList = fileDf.iloc[:, 0].tolist()

    return jsonify([name for name in namesList[:5] if name.strip() != ""])

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
