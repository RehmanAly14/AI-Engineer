import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from pydantic import BaseModel
load_dotenv()

my_api_key = os.getenv("Groq_API_KEY")
if not my_api_key:
    raise ValueError("Groq_API_KEY not found in environment variables.")

client = Groq(api_key=my_api_key)

model = "llama-3.3-70b-versatile"

class Ticket (BaseModel):
    name: str
    age: str
    phone_number: str

schema = Ticket.model_json_schema()

response_format = {
    'type': "json_object",
}

system_prompt = f"""You are a helpful assistant that extracts information from text and returns it in JSON format according to the following schema: {schema}"""

role = 'user'
text = 'hi! this is Rehman , iam a software engineer and i love to code and learn new things. i am very passionate about technology and always eager to explore new advancements in the field. My age is 20 and my phone num is 34455255 '
prompt = f""" Please extract the following information from the text: Name, Age, Phone Number. The text is: '{text}'"""

message_system ={
    "role": "system",
    "content": system_prompt
}
message = {
    "role": role,
    "content": prompt
}
message_list = [message_system, message]
response = client.chat.completions.create(model=model, messages=message_list,response_format=response_format)
# print(response.choices[0].message.content)





import json
raw_json = response.choices[0].message.content
data_file = json.loads(raw_json)
ticket = Ticket(**data_file)


print(ticket.name)
print(ticket.age)
print(ticket.phone_number)