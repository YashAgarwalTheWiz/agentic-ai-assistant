from state import AgentState
from memory.short_term import get_messages
from memory.long_term import get_long_term_memory
from memory.long_term import long_term_collection

def memory_retrieval(state: AgentState) -> dict:
    chat_id = state['chat_id']
    messages = get_messages(chat_id)
    formatted = [{"role": m[2], "content": m[3]} for m in messages]
    long_term_messages = get_long_term_memory(long_term_collection, state['user_input'], 'default_user')
    return {"messages": formatted, 'long_term_memory': long_term_messages}