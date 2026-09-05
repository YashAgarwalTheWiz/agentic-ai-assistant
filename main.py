from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.environ.get('GROQ_API_KEY')

client = Groq(api_key=API_KEY)

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[{"role": "user", "content": "hi"}]
)

print(response.choices[0].message.content)