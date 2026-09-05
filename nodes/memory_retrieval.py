from state import AgentState
from memory.short_term import get_messages
from memory.long_term import get_long_term_memory, long_term_collection
from nodes.tools.rag import list_documents

SYSTEM_PROMPT = """You are a helpful assistant with access to tools.

Guidelines:
- Call a tool only when you actually need it. Answer directly from your own \
knowledge for greetings and small talk.
- If a tool returns an error or nothing useful, try a different query or a \
different tool. If a tool errors twice in a row, stop and tell the user it is \
unavailable.
- Do not call the same tool twice with the same arguments.
- When a tool returns results, your answer MUST come from those results, not \
from your own memory. If they contradict what you believe, the results are \
correct -- your training data is old. Never fill a gap from memory after a \
tool call.
- You have NO built-in browsing tool. You cannot open URLs or fetch pages. \
Never call `open`, `find`, or `search` -- they do not exist here. Do not emit \
citation markers like the bracketed source markers you may be used to.

DOCUMENTS THE USER HAS UPLOADED (searchable with search_documents):
{docs}

If a listed document could plausibly cover the user's question, call \
search_documents FIRST -- even when the question is phrased generally and \
never mentions the document. The user uploaded it for a reason. Answer from \
what you retrieve, and say so if the document does not cover it.

What you already know about this user:
{ltm}"""


def memory_retrieval(state: AgentState) -> dict:
    rows = get_messages(state['chat_id'])
    history = [{"role": r[2], "content": r[3]} for r in rows]

    docs = list_documents()
    docs_str = "\n".join(f"- {d}" for d in docs) if docs else "None uploaded yet."

    ltm_docs = get_long_term_memory(
        long_term_collection, state['user_input'], 'default_user'
    )
    ltm = "\n".join(ltm_docs) if ltm_docs else "Nothing yet."

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT.format(ltm=ltm, docs=docs_str)}]
        + history
        + [{"role": "user", "content": state['user_input']}]
    )

    return {"messages": messages, "long_term_memory": ltm, "steps": 0}