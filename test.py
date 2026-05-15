from agent import workflow
from memory.short_term import create_chat, init_db
from nodes.tools.rag import init_rag,ingest_pdf

init_db()
init_rag()

initial_state={
    'user_input':'What is writtten in the pdf ?',
    'chat_id':create_chat(),
    'long_term_memory': '',
'query_type': 'rag',
'response': '',
'tool_result': ''
}

ingest_pdf(r'C:\Users\yash\OneDrive\Desktop\Chatbot\TCS_joining_letter.pdf')

result = workflow.invoke(initial_state)
print(result['response'])
print(result['query_type'])
print(result['tool_result'])