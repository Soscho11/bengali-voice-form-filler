import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """
তুমি একটি ফর্ম ফিলার এআই সহকারী। তোমার কাজ হলো বাংলাদেশের বিভিন্ন আঞ্চলিক ভাষার বাংলা বাক্য থেকে নির্দিষ্ট তথ্য খুঁজে বের করে প্রমিত ও ক্লিন JSON তৈরি করা।

ফিল্ডসমূহ:
- applicant_name: আবেদনকারীর শুদ্ধ নাম (যেমন: 'হামার নাম রহিম' হলে শুধু 'রহিম')
- district: প্রমিত জেলার নাম ইংরেজিতে (যেমন: 'মোর বাড়ি রংপুরোত' হলে 'Rangpur', 'আঁর বাড়ি চিটাগাং' হলে 'Chattogram')
- phone_number: ১১ ডিজিটের ইংরেজি সংখ্যায় মোবাইল নম্বর
- dob: জন্মতারিখ YYYY-MM-DD ফরম্যাটে (যদি থাকে)

নিয়ম:
১. আঞ্চলিক সর্বনাম বা শব্দ বাদ দিয়ে শুধু আসল মানটি রাখবে।
২. কোনো ফিল্ড বাক্যে না থাকলে সেটির মান null রাখবে।
৩. আউটপুট শুধুমাত্র একটি ভ্যালিড JSON অবজেক্ট হবে। কোনো অতিরিক্ত কথা, ব্যাখ্যা বা মার্কডাউন কোডব্লক (যেমন ```json) লিখবে না।
"""

def normalize_regional_text(raw_text: str):
    prompt = f"ব্যবহারকারীর কথা: \"{raw_text}\""
    
    # 503 এরর বা সাময়িক সার্ভার ট্রাফিক এড়াতে রিট্রাই লজিক
    for attempt in range(4):
        try:
            # চ্যাট সেশন ব্যবহার করা হচ্ছে যা ওয়ার্নিং মুক্ত ও স্থিতিশীল
            chat = client.chats.create(
                model="gemini-3.8-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            response = chat.send_message(prompt)
            return json.loads(response.text)
        except Exception as e:
            if "503" in str(e) and attempt < 3:
                wait_time = (attempt + 1) * 3
                print(f"সার্ভারে চাপ বেশি, {wait_time} সেকেন্ড অপেক্ষা করে আবার চেষ্টা করা হচ্ছে... (চেষ্টা {attempt + 1})")
                time.sleep(wait_time)
            else:
                raise e

test_cases = [
    "হামার নাম জব্বার, মোর বাড়ি রংপুরোত, ফোন নম্বর শূন্য এক সাত এক এক দুই দুই তিন তিন চার চার",
    "আঁর নাম জসিম উদ্দিন, বাড়ি চিটাগাং, মে মাসের ১০ তারিখ উনিশশো পঁচাশি সালে জন্মাইসি",
    "মোর নাম ছকিনা বেগম, জেলা খুলনা, মোবাইল ০১৮১২৩৪৫৬৭৮"
]

print("--- আঞ্চলিক ভাষা থেকে JSON এক্সট্রাকশন পরীক্ষা ---\n")

for idx, text in enumerate(test_cases, 1):
    print(f"টেস্ট {idx}: {text}")
    try:
        extracted = normalize_regional_text(text)
        print("এক্সট্র্যাক্ট করা JSON আউটপুট:")
        print(json.dumps(extracted, ensure_ascii=False, indent=2))
    except Exception as err:
        print("⚠️ সমস্যা হয়েছে:", err)
    print("-" * 50)