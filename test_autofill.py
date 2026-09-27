import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from playwright.sync_api import sync_playwright

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
তুমি একটি ফর্ম ফিলার এআই সহকারী। আঞ্চলিক বাংলা বাক্য থেকে তথ্য ফিল্টার করে ক্লিন JSON তৈরি করো।
ফিল্ডসমূহ:
- applicant_name: শুদ্ধ নাম
- district: প্রমিত জেলা ইংরেজিতে (যেমন: Rangpur, Chattogram, Khulna, Dhaka)
- phone_number: ১১ ডিজিটের ইংরেজি সংখ্যায় মোবাইল নম্বর
- dob: জন্মতারিখ YYYY-MM-DD ফরম্যাটে (যদি থাকে)
আউটপুট শুধুমাত্র ভ্যালিড JSON অবজেক্ট হবে।
"""

def extract_info(voice_text: str):
    print(f"\n🗣️ ব্যবহারকারীর কথা: \"{voice_text}\"")
    print("🤖 Gemini তথ্য প্রসেস করছে...")
    
    # 503 ব্যাকঅফ রিট্রাই
    for attempt in range(3):
        try:
            chat = client.chats.create(
                model="gemini-3.8-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json"
                )
            )
            res = chat.send_message(f"ব্যবহারকারীর কথা: \"{voice_text}\"")
            data = json.loads(res.text)
            print(f"✅ এক্সট্র্যাক্ট করা ডেটা: {data}")
            return data
        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(3)
            else:
                raise e

def autofill_form(data):
    html_path = Path(__file__).parent.resolve() / "form.html"
    
    with sync_playwright() as p:
        # headless=False দিলে নিজের চোখে ব্রাউজার ওপেন হতে দেখা যাবে
        browser = p.chromium.launch(headless=False, slow_mo=700)
        page = browser.new_page()
        page.goto(f"file://{html_path}")
        
        print("\n🚀 ব্রাউজারে স্বয়ংক্রিয়ভাবে ফর্ম ফিলাপ শুরু হচ্ছে...")

        if data.get("applicant_name"):
            page.fill("#name", data["applicant_name"])

        if data.get("district"):
            page.select_option("#district", value=data["district"])

        if data.get("phone_number"):
            page.fill("#phone", data["phone_number"])

        if data.get("dob"):
            page.fill("#dob", data["dob"])

        print("✨ ফর্ম পূরণ সম্পন্ন! ৩ সেকেন্ড পর সাবমিট বাটনে ক্লিক করা হবে...")
        time.sleep(3)
        
        # সাবমিট বাটনে ক্লিক
        page.click("button")
        time.sleep(3)
        browser.close()

if __name__ == "__main__":
    # আঞ্চলিক ভাষার একটি ডেমো ইনপুট
    sample_voice_input = "হামার নাম জব্বার, মোর বাড়ি রংপুরোত, ফোন নম্বর শূন্য এক সাত এক এক দুই দুই তিন তিন চার চার"
    
    try:
        extracted_data = extract_info(sample_voice_input)
        autofill_form(extracted_data)
    except Exception as e:
        print("⚠️ সমস্যা হয়েছে:", e)