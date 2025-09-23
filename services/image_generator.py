import requests
import time
from django.conf import settings

API_KEY = settings.KIE_API_KEY  # Set this in your environment

if not API_KEY:
    raise Exception("Set KIE_API_KEY env var first") 

class Image_generator():
    def __init__(self , api_key=API_KEY):
        self.api_key = api_key
        self.base_url = "https://kieai.erweima.ai/api/v1/gpt4o-image/"
        self.HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}"
        }
    def create_task_image(self ,prompt, aspect_ratio="1:1"):
        resp = requests.post(url=f"{self.base_url}generate", json={"prompt": prompt, "aspectRatio": aspect_ratio}, headers=self.HEADERS)
        resp.raise_for_status()

        print(resp.json()['code'])
        if resp.json()['code'] == 200:
            task_id = resp.json()['data']['taskId']
            return task_id
        else:
            return None
            # raise Exception("Generation failed:", resp.json()['code'])
        
    def check_status(self, task_id):
        url = f"{self.base_url}record-info"
        resp = requests.get(url, params={"taskId": task_id}, headers=self.HEADERS)
        resp.raise_for_status()
        
        print(resp.json())
        if resp.json()['code'] == 200:
            return resp.json()
        else:
            raise Exception("status", resp.json())

    def download(self ,image_info, dest,):
        img_resp = requests.get(image_info['data']['response']['resultUrls'][0])
        img_resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(img_resp.content)

        print("Image saved to lake.png")






