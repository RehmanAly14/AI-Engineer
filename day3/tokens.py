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
prompt1 = "hi, how are you?"
prompt2 = "what is machine learning?"
prompt3 = "write easy in 500 words about Web Development"

for prompt in [prompt1, prompt2, prompt3]:
    message = {
    "role": role,
    "content": prompt
    }
    message_list = [ message]
    response = client.chat.completions.create(model=model, messages=message_list,max_tokens=100)
    print(f"Prompt: {prompt} --> your token : {response.usage.prompt_tokens} --> completion token : {response.usage.completion_tokens} --> total token : {response.usage.total_tokens} finish_reason : {response.choices[0].finish_reason} ")