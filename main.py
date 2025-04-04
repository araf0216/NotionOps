import os
import requests
import json
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)

def notionOps(op, intkey, dbTitle=None, data=None):

    def initConnection(intkey):
        dbs = {}

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
            print(curTitle)
            dbs[curTitle] = db["id"]
            if curTitle == dbTitle:
                dbKey = db["id"]
                break

        if dbKey is None:
            print("No match found to: ", dbTitle)
        else:
            print(dbKey)
            
        return dbs

    def getDb(intkey, dbTitle, data):
        print("updateDb triggered")

        dbKey = initConnection(intkey)

        print(dbKey)

        # dbObj = json.loads(dbObj)

        # res = dbObj["results"]

        # for i in res:
        #     print(i["properties"]["title"]["title"][0]["text"]["content"])
        
        # headers = {
        #   "Authorization": "Bearer " + intkey,
        #   "Content-Type": "application/json",
        #   "Notion-Version": "2022-06-28",
        # }
    
        # update_url = "https://api.notion.com/v1/pages/" + intkey + "/" + dbkey
    
        # res = requests.patch(update_url, headers=headers, data=data).json()
    
        # print(json.dumps(res, indent=2, ensure_ascii=False))
        

    match op:
        case "init":
            return initConnection(intkey)

        case "get":
            if dbTitle and data:
                getDb(intkey, dbTitle, data)
            else:
                print("Error: dbkey and data are required")

        # case "update":
        #     if dbkey and data:
        #         updateDb(intkey, dbkey, data)
        #     else:
        #         print("Error: dbkey and data are required")

@app.route('/api', methods=('GET', 'POST'))
def api():
    res = notionOps("init", key)
    print(res)
    # return res

@app.route('/', methods=('GET', 'POST'))
def index():
    key = "empty"
    res = None
    if request.method == 'POST':
        key = request.form['key']
        print("Received Key: " + key)

        if len(key) > 0:
            res = notionOps("init", key)
            # print(res)
    
        
    return render_template('index.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=5000, debug=True)
