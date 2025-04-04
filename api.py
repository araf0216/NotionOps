import json
import requests

intsec = input()

headers = {
  "Authorization": "Bearer " + intsec,
  "Content-Type": "application/json",
  "Notion-Version": "2022-06-28",
}

search_url = "https://api.notion.com/v1/search"

res = requests.post(search_url, headers=headers).json()

print(json.dumps(res, indent=2, ensure_ascii=False))

