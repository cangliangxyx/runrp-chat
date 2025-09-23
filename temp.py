import requests
import json

url = "https://chat.cloudapi.vip/v1beta/models/gemini-2.5-pro:generateContent"

payload = json.dumps({
   "contents": [
      {
         "parts": [
            {
               "text": "Explain how AI works in a few words"
            }
         ]
      }
   ],
   "generationConfig": {
      "thinkingConfig": {
         "thinkingBudget": 128,
         "includeThoughts": True
      }
   }
})
api_key = "sk-YBnNIMqAlZex02fSNjijK6qyqVsI8hzCogIab8ED3IW3REHZ"
# api_key = "sk-GFP62OhkTplx4DhkMNjwBhYAogftxZM6znbz2l8PDwc5CfBE"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
# headers = {
#    'Authorization': 'Bearer {sk-YBnNIMqAlZex02fSNjijK6qyqVsI8hzCogIab8ED3IW3REHZ}',
#    'Content-Type': 'application/json'
# }

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)