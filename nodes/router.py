from state import AgentState
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY=os.environ.get('GROQ_API_KEY')

def router(state:AgentState)->dict:
    if state['query_type'] == 'rag':
        return {'query_type': 'rag'}
    
    client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=API_KEY
        )
    response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
            {"role": "system", "content": '''You are a router. Based on the user query, return ONLY one word.
            Your options are:
            - chat: for general conversation
            - search: for questions needing current/real-time information
            - rag: for questions about uploaded documents or files
            - structured: for requests needing structured data output
            Return nothing else. No explanation. Just the word.'''},{"role": "user", "content": state['user_input']}]
        )
    return {'query_type':response.choices[0].message.content.strip().lower()}