from state import AgentState
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from nodes.tools.rag import query_rag
from nodes.tools.search import search
load_dotenv()

API_KEY=os.environ.get('GROQ_API_KEY')

def clean_query(user_input: str) -> str:
    client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=API_KEY
        )
    response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
            {"role": "system", "content": f'''Extract a clean, concise search query from the user message. Return only the query, nothing else.'''},{"role": "user", "content": user_input}]
        )
    return response.choices[0].message.content


def llm_call(state:AgentState)->dict:
        
    if state['query_type'] == 'search':
        state['tool_result'] = search(clean_query(state['user_input']))
    elif state['query_type'] == 'rag':
        state['tool_result'] = query_rag(state['user_input'])

    tool_context = f"Tool Results: {state['tool_result']}" if state['query_type'] in ['search', 'rag'] else ""

    client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=API_KEY
        )
    if state['query_type']=='structured':
        response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
            {"role": "system", "content": f'''You are a helpful assistant. Here is what you know about the user: {state['long_term_memory']} {tool_context}. Return your response as a valid JSON array only. No explanation, no markdown, just raw JSON.'''},
            *state['messages'],{"role": "user", "content": state['user_input']}]
        )
        return {
            'structured_output': json.loads(response.choices[0].message.content),'response': response.choices[0].message.content,'tool_result': state['tool_result']
            }
    else:
        response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                {"role": "system", "content": f'''You are a helpful assistant. Here is what you know about the user: {state['long_term_memory']} {tool_context}'''},
                *state['messages'],{"role": "user", "content": state['user_input']}]
            )
    return {'response':response.choices[0].message.content,'tool_result': state['tool_result']}