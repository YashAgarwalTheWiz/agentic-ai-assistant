import os
from openai import OpenAI
from dotenv import load_dotenv

from state import AgentState
from memory.short_term import save_message, chat_name, get_messages
from memory.long_term import save_long_term_memory, long_term_collection

load_dotenv()

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get('GROQ_API_KEY'),
)
MODEL = os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')


def _existing_profile(user_id: str) -> str:
    """Fetch whatever is currently stored for this user, or empty text
    if nothing has been saved yet."""
    try:
        result = long_term_collection.get(ids=[f"profile:{user_id}"])
        docs = result.get('documents') or []
        return docs[0] if docs else ""
    except Exception:
        return ""


def memory_writer(state: AgentState) -> dict:
    response = state.get('response') or (
        "I wasn't able to finish that within my step limit. "
        "Could you narrow the question down?"
    )

    is_first_turn = len(get_messages(state['chat_id'])) == 0

    save_message(state['chat_id'], 'user', state['user_input'])
    save_message(state['chat_id'], 'assistant', response)

    if is_first_turn:
        chat_name(state['chat_id'], state['user_input'][:30])

    existing = _existing_profile('default_user')

    facts = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content":
                "You maintain a running profile of durable facts about the USER: "
                "name, job, location, preferences, ongoing goals. "
                "You will be shown the EXISTING profile plus the newest exchange. "
                "Return the FULL updated profile, keeping everything still true "
                "and adding or correcting anything new -- do not drop existing "
                "facts just because this turn didn't repeat them. "
                "Ignore one-off questions and anything about the world rather "
                "than the user. If there is nothing durable in total, return "
                "exactly NONE."},
            {"role": "user", "content":
                f"EXISTING PROFILE:\n{existing or '(nothing yet)'}\n\n"
                f"NEWEST EXCHANGE:\nUser: {state['user_input']}\n"
                f"Assistant: {response}"},
        ],
    ).choices[0].message.content

    if facts and 'NONE' not in facts.strip().upper():
        save_long_term_memory(long_term_collection, facts, 'default_user')

    return {"response": response}