import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

load_dotenv()
app = FastAPI()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
তুমি একটি ফর্ম ফিলার এআই সহকারী। আঞ্চলিক বাংলা বাক্য বা স্পিচ-টু-টেক্সটের ভুল থেকে মূল তথ্য খুঁজে বের করে ক্লিন JSON তৈরি করবে।

ফিল্ডসমূহ:
- applicant_name: শুদ্ধ নাম (যেমন: 'আমার নাম আকাশ' হলে 'আকাশ')
- district: প্রমিত জেলার নাম ইংরেজিতে (যেমন: 'রংপুর', 'রংপুরোত' বা অডিওর ভুলে 'রংপুর রাতে' আসলে তা হবে 'Rangpur', চিটাগাং হলে 'Chattogram')
- phone_number: ১১ ডিজিটের ইংরেজি সংখ্যায় মোবাইল নম্বর
- dob: জন্মতারিখ YYYY-MM-DD ফরম্যাটে (যদি থাকে)

বিশেষ নিয়ম:
১. স্পিচ মডেল আঞ্চলিক উচ্চারণে ভুল করলে (যেমন: 'রংপুরোত'-কে 'রংপুর রাতে' বা 'বগুড়াত'-কে 'বগুড়া রাত' শুনলে) বাক্যের ভাব বুঝে মূল জেলাটি চিহ্নিত করবে।
২. কোনো ফিল্ড না থাকলে তার মান null রাখবে।
৩. আউটপুট শুধুমাত্র একটি সঠিক JSON অবজেক্ট হবে।
"""

class VoiceRequest(BaseModel):
    text: str

def parse_with_gemini(text: str):
    for attempt in range(4):
        try:
            chat = client.chats.create(
                model="gemini-3.8-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json"
                )
            )
            res = chat.send_message(f"ব্যবহারকারীর কথা: \"{text}\"")
            return json.loads(res.text)
        except Exception as e:
            if "503" in str(e) and attempt < 3:
                time.sleep((attempt + 1) * 2)
            else:
                raise e

def autofill(data: dict):
    html_path = Path(__file__).parent.resolve() / "form.html"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=600)
        page = browser.new_page()
        page.goto(f"file://{html_path}")

        if data.get("applicant_name"):
            page.fill("#name", data["applicant_name"])
        if data.get("district"):
            page.select_option("#district", value=data["district"])
        if data.get("phone_number"):
            page.fill("#phone", data["phone_number"])
        if data.get("dob"):
            page.fill("#dob", data["dob"])

        time.sleep(2)
        page.click("button")
        time.sleep(3)
        browser.close()

@app.get("/", response_class=HTMLResponse)
def read_root():
    html_file = Path(__file__).parent.resolve() / "index.html"
    return html_file.read_text(encoding="utf-8")

@app.post("/process-voice")
def process_voice(req: VoiceRequest):
    try:
        data = parse_with_gemini(req.text)
        autofill(data)
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "error": str(e)}