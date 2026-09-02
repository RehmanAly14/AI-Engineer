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
prompt = "Write a poem about the beauty of nature."

message = {
    "role": role,
    "content": prompt
}
message_list = [message]

response = client.chat.completions.create(model=model, messages=message_list)
print(response.choices[0].message)