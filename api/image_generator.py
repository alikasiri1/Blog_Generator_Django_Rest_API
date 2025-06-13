import requests
import time
# from django.conf import settings

API_KEY = 'c2a9b3212fce020e0b04a429903cd512' # settings.KIE_API_KEY  # Set this in your environment

if not API_KEY:
    raise Exception("Set KIE_API_KEY env var first")

class Image_generator(API_KEY):
    def __init__(self ):
        self.base_url = "https://kieai.erweima.ai/api/v1/gpt4o-image/"
        self.HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
        }
    def create_task(self ,prompt, aspect_ratio="1:1"):
        resp = requests.post(url=f"{self.base_url}generate", json={"prompt": prompt, "aspectRatio": aspect_ratio}, headers=self.HEADERS)
        resp.raise_for_status()

        print(resp.json()['code'])
        if resp.json()['code'] == 200:
            self.task_id = resp.json()['data']['taskId']
        else:
            raise Exception("Generation failed:", resp.json()['code'])
        
    def check_status(self):
        url = f"{self.base_url}record-info"
        resp = requests.get(url, params={"taskId": self.task_id}, headers=self.HEADERS)
        resp.raise_for_status()
        
        print(resp.json())
        if resp.json()['code'] == 200:
            self.image_info = resp.json()
        else:
            raise Exception("status", resp.json())

    def download(self ,dest):
        img_resp = requests.get(self.image_info['data']['response']['resultUrls'][0])
        img_resp.raise_for_status()
        with open(dest, "wb") as f:
            f.write(img_resp.content)

        print("Image saved to lake.png")



image_generator = Image_generator(API_KEY)
image_generator.create_task("A serene lake at sunrise")
image_generator.check_status()
image_generator.download('lake.png')


