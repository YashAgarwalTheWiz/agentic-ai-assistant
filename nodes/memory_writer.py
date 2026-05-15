from state import AgentState
from openai import OpenAI
from dotenv import load_dotenv
import os
from memory.short_term import save_message,chat_name
load_dotenv()
from memory.long_term import save_long_term_memory,long_term_collection

API_KEY=os.environ.get('GROQ_API_KEY')

def memory_writer(state:AgentState)->dict:
    save_message(state['chat_id'],'user',state['user_input'])
    save_message(state['chat_id'],'assistant',state['response'])
    client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=API_KEY
        )
    response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {'role':'system','content':'''
                        Extract any important facts about the user from this conversation. 
                        If nothing important, return "NONE".
                    '''},{'role':'user','content':state['user_input']},{'role':'assistant','content':state['response']}
                ]
        )
    existing_messages=state['messages']
    if len(existing_messages)==0:
        chat_name(state['chat_id'],state['user_input'][:30])
    facts=response.choices[0].message.content
    if facts.strip().upper()!='NONE':
        save_long_term_memory(long_term_collection,facts,'default_user')
    return {}