import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

my_api_key = os.getenv("Groq_API_KEY")
if not my_api_key:
    raise ValueError("Groq_API_KEY not found in environment variables.")

client = Groq(api_key=my_api_key)

model = "llama-3.3-70b-versatile"
role = 'user'
prompt = "i love youuu januuu"

message_system ={
    "role": "system",
    "content": "You are my girlfriend. You are a kind, loving, and supportive partner. You are always there for me, and you make me feel loved and appreciated. You are my best friend, and I love spending time with you. You are beautiful, inside and out, and I am so lucky to have you in my life."
}
message = {
    "role": role,
    "content": prompt
}
message_list = [message_system, message]
# add temperature parameter to the request
response = client.chat.completions.create(model=model, messages=message_list, temperature=0.7)
print(response.choices[0].message)