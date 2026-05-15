from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY=os.environ.get('SAMBANOVA_API_KEY')

client = OpenAI(
    base_url="https://api.sambanova.ai/v1",
    api_key=API_KEY
)
response = client.chat.completions.create(
    model="Meta-Llama-3.3-70B-Instruct",
    messages=[{"role": "user", "content": "hi"}]
)
print(response.choices[0].message.content)