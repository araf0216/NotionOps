import os
import requests
import json
import math
import pandas as pd
from flask import Flask, redirect, render_template, request, session, url_for, jsonify
from threading import Thread, Event

app = Flask(__name__)

integrationKey = None
selectedDB = None
selectedRows = None
keysList = []
selectedProp = [{}]
retrieved = []
databaseInfo = None
toUpdate = []

progLevel = {"value": 0, "target": 0, "status": "idle"}

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
            "filter": {}
        }

        chunkCap = 100
        chunk = {
            "or": [], # max capacity = chunkCap
        }
        chunksC = 1
        
        global retrieved
        retrieved = []
        que_url = "https://api.notion.com/v1/databases/" + dbKey + "/query"
        progLevel["target"] = max(math.ceil(len(rows) / 100), 1)

        # populating payload with submitted name property values
        for row in rows:
            row_filter = {
                "property": "Name",
                "title": {
                    "equals": row
                }
            }


            # append row to current chunk
            chunk["or"].append(row_filter)

            # check if current chunk size is at max cap OR if final row reached
            if (len(chunk["or"]) == chunkCap or row == rows[-1]):
                # add chunk to the payload
                print(f"Retrieving {chunksC}th Batch - Out of {progLevel['target']} Total Batches")

                payload["filter"] = chunk

                queryRes = requests.post(que_url, headers=headers, json=payload).json()
                retrieved.extend(queryRes["results"])
                progLevel["value"] += 1

                # restore chunk to new empty chunk
                chunk = None
                chunk = {
                    "or": [], # max capacity = chunkCap
                }

                # increment chunk number
                chunksC += 1

        # for logging retrieved data - pre-update
        # with open("data.json", "w") as file:
        #     json.dump(retrieved, file, indent=4)


        global databaseInfo
        
        db_url = "https://api.notion.com/v1/databases/" + dbKey
        res = requests.get(db_url, headers=headers).json()

        databaseInfo = res

        return res
    
    def updateDb():
        print("update action triggered")

        global selectedDB
        global retrieved
        global selectedProp
        global toUpdate
        global progLevel

        if retrieved == None or toUpdate == [] or selectedProp == []:
            return jsonify("failed")
        
        global keysList
        map = {}

        cache = {}
        def valTransformer(val, typ):
            match typ:
                case "date":
                    return val.strftime("%Y-%m-%d")

                case "relation":
                    if cache != {}:
                        return cache["id"]
                    
                    cache["type"] = "Name"
                    cache["typeVal"] = val

                    headers = {
                        "Authorization": "Bearer " + intkey,
                        "Content-Type": "application/json",
                        "Notion-Version": "2022-06-28",
                    }

                    payload = {
                        "filter": {
                            "property": cache["type"],
                            "title": {
                                "equals": cache["typeVal"]
                            }
                        }
                    }

                    queUrl = "https://api.notion.com/v1/databases/" + selectedDB["db"] + "/query"

                    queryRel = requests.post(queUrl, headers=headers, json=payload).json()

                    cache["id"] = queryRel["results"][0]["id"]

                    return cache["id"]

        if "map" in toUpdate:
            fpath = "Murano Names.xlsx"

            fileDf = pd.read_excel(fpath)
            # fileDf = pd.read_excel(fpath, sheet_name=3)

            if keysList == []:
                keysList = fileDf.iloc[:, 0].tolist()
                keysList = [name for name in keysList[:] if name.strip() != ""]

            # future extension - user selects which property is key and which is value
            valuesList = fileDf.iloc[:len(keysList), 1].tolist()

            map = {key: value for key, value in zip(keysList, valuesList)}
            # duplicate each key-value pair to allow for case-insensitive search
            map.update({key.lower(): value for key, value in map.items()})

            # print(map)
            # return "failed"
        
        progLevel["target"] = len(retrieved)

        # queryRes contains the necessary rows and their page id's
        for res in retrieved:
            pageID = res["id"]

            rowUrl = "https://api.notion.com/v1/pages/" + pageID

            headers = {
                "Authorization": "Bearer " + intkey,
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }

            properties = {
                "properties": {
                    # selectedProp[0]["prop"]: val,
                    # "Report Received Date": {
                    #     "date": {
                    #         "start": "1996-04-20"
                    #     }
                    # }
                }
            }

            for prop, val in zip(selectedProp, toUpdate):
                
                # check update is uniform vs. mapped to apply necessary formatting
                if val == "map":
                    val = res["properties"]["Name"]["title"][0]["text"]["content"]
                    val = map[val] if val in map else map[val.lower()]

                match prop["type"]:

                    # type checkbox - only uniform atm
                    case "checkbox":
                        val = {
                            "checkbox": val == "checked"
                        }

                    # type date - only mapped atm
                    case "date":
                        val = {
                            "date": {
                                "start": valTransformer(val, "date")
                            }
                        }
                    
                    # type number - only mapped atm
                    case "number":
                        val = {
                            "number": val
                        }
                    
                    # type relation - only uniform, current DB atm
                    case "relation":
                        val = {
                            "relation": [
                                {
                                    "id": valTransformer(val, "relation")
                                }
                            ]
                        }

                properties["properties"][prop["prop"]] = val

            res = requests.patch(rowUrl, headers=headers, json=properties).json()
            
            if res == {} or res["object"] == "error":
                print(res)
                return "failed"

            progLevel["value"] += 1
        
        return "complete"



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

    # receiving testing integration token from front end
    if request.method == 'POST' and integrationKey == None:
        # print("triggered POST and no IntKey")
        key = request.form['key']
        # print("Received Key: " + key)

        if key.strip() != "":
            res = notionOps("init", key)
            # print("intkey confirmed with result:", res)
            integrationKey = key
        
        return jsonify(res)

    key = integrationKey
    global selectedDB
    global selectedRows
    global selectedProp
    global databaseInfo
    global toUpdate
    global progLevel

    # retrieving user-selected DB from api
    if request.method == 'POST' and selectedDB == None:
        # print("triggered submission of database AND rows selections")
        selectedDB = request.get_json()
        db = selectedDB
        # print("got selected db in api")
        print(db)

        selectedRows = db["rows"]

        # compartmentalized executer of the retrieval operation
        def retrievalTask():
            global progLevel

            progLevel = {"value": 0, "target": 1, "status": "started"}
            res = notionOps("get", db["int"], db["db"])
            progLevel["status"] = "complete"
            return res
        
        # pass the retrieval executer into a thread for the execution to keep running in the background
        #  - using threading techniques allows for sending live progress updates to the front-end
        retrievalThread = Thread(target=retrievalTask)
        retrievalThread.start()

        return jsonify("started")

    # gathering available properties from selected DB retrieved
    elif request.method == 'GET' and selectedProp[-1] == {}:
        res = databaseInfo
        propsRes = res["properties"]
        props = [{prop: propsRes[prop]} for prop in [p for p in propsRes][::-1]]
        # if selectedProp[-1] != {}:
        #     selectedProp.append({})
        return jsonify(props)
    
    # receiving and storing user-selected property to update
    elif selectedProp[-1] == {}:
        print("triggered property submission")
        prop = request.get_json()
        selectedProp.pop()
        selectedProp.append(prop)
        res = databaseInfo["properties"][prop["prop"]]
        return jsonify(res)
    
    # submitting next state value of update to perform
    elif len(selectedProp) > 0:
        print("triggered update")

        # print("Selected property to update", selectedProp["prop"])

        value = request.get_json()
        toUpdate.append(value["value"])

        # if submitted prop is not final, return to selection of next prop
        if value["final"] != None and value["final"] == False:
            print("Prop select continues")
            selectedProp.append({})
            return jsonify("anotha one")

        # compartmentalized executer of the actual update operation
        def updateTask():
            global progLevel
            
            progLevel = {"value": 0, "target": 1, "status": "started"}
            res = notionOps("update", key)
            progLevel["status"] = res
            return res

        # pass the update executer into a thread for update task to keep running in the background
        #  - using threading techniques allows for sending live progress updates to the front-end
        updateThread = Thread(target=updateTask)
        updateThread.start()

        print("Status right before return", progLevel["status"])

        return jsonify(progLevel["status"])

    return jsonify({})

@app.route('/', methods=('GET', 'POST'))
def index():

    global integrationKey
    integrationKey = None

    global selectedDB
    selectedDB = None

    global selectedRows
    selectedRows = None

    global retrieved
    retrieved = []

    global keysList
    keysList = []

    global selectedProp
    selectedProp = [{}]

    global databaseInfo
    databaseInfo = None

    global toUpdate
    toUpdate = []

    global progLevel
    progLevel = {"value": 0, "target": 0, "status": "idle"}

    return render_template('index.html')

@app.route('/progress', methods=('GET', 'POST'))
def progress():
    global progLevel

    if progLevel["status"] == "complete":
        completeProg = progLevel
        progLevel = {"value": 0, "target": 0, "status": "idle"}
        print(completeProg)
        print(progLevel)
        return jsonify(completeProg)
        
    return jsonify(progLevel)

@app.route('/file', methods=('GET', 'POST'))
def file():

    global keysList

    fpath = "Murano Names.xlsx"
    # fpath = "Murano AUMs.xlsx"

    if not os.path.exists(fpath):
        print("no such file exists")
        return jsonify(False)
        
    fileDf = pd.read_excel(fpath)
    # fileDf = pd.read_excel(fpath, sheet_name=3)
    keysList = fileDf.iloc[:, 0].tolist()
    keysList = [name for name in keysList[:] if name.strip() != ""]

    return jsonify(keysList)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000)
