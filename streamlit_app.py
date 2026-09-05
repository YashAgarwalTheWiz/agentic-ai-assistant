import json

import requests
import streamlit as st

URL = 'http://127.0.0.1:8000'

if 'chat_id' not in st.session_state:
    st.session_state.chat_id = None
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'ingested' not in st.session_state:
    st.session_state.ingested = set()
if 'pending' not in st.session_state:
    # {thread_id, actions, user_input} while a turn is parked at the gate
    st.session_state.pending = None


def record_turn(user_input, res):
    st.session_state.messages.extend([
        {'role': 'user', 'content': user_input},
        {'role': 'assistant', 'content': res['response'],
         'tools': res.get('tools_used'), 'steps': res.get('steps', 0)},
    ])


def handle(res, user_input):
    """Route a /chat or /resume response: park at the gate, or finish."""
    if res.get('status') == 'pending_approval':
        st.session_state.pending = {
            'thread_id': res['thread_id'],
            'actions': res['actions'],
            'user_input': user_input,
        }
    else:
        st.session_state.pending = None
        record_turn(user_input, res)


def resume(decisions, pending):
    with st.spinner('Working...'):
        r = requests.post(URL + '/resume', json={
            'thread_id': pending['thread_id'],
            'decisions': decisions,
        })
    if r.status_code != 200:
        st.error(f"Resume failed ({r.status_code}).")
        st.code(r.text[:1000] or "(empty response)")
        st.stop()
    handle(r.json(), pending['user_input'])
    st.rerun()


def check_args(tool, arguments):
    """Ask the server which required fields are missing. Never blocks on
    a network hiccup -- the server validates again before executing."""
    try:
        r = requests.post(URL + '/validate_args',
                          json={'tool': tool, 'arguments': arguments})
        return r.json().get('missing', []) if r.status_code == 200 else []
    except requests.RequestException:
        return []


with st.sidebar:
    if st.button('New chat'):
        st.session_state.chat_id = requests.post(URL + '/new_chat').json()
        st.session_state.messages = []
        st.session_state.pending = None
        st.rerun()

    for name, chat_id in requests.get(URL + '/chats').json():
        if st.button(name or "New Chat", key=chat_id):
            st.session_state.chat_id = chat_id
            st.session_state.messages = requests.get(URL + f'/messages/{chat_id}').json()
            st.session_state.pending = None
            st.rerun()

    st.divider()

    file = st.file_uploader("Upload PDF", type=["pdf"], key="pdf_uploader")
    if file and file.name not in st.session_state.ingested:
        res = requests.post(URL + '/upload_pdf', files={'pdf': file})
        if res.status_code == 200:
            st.session_state.ingested.add(file.name)
            st.success(res.json()['message'])
        else:
            st.error(res.json().get('detail', 'Upload failed'))

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['content'])
        if message.get('tools'):
            st.caption(f"🔧 {', '.join(message['tools'])} · {message['steps']} steps")


# ---------------------------------------------------------------- approval gate
pending = st.session_state.pending

if pending:
    with st.chat_message('user'):
        st.write(pending['user_input'])

    st.warning("This needs your approval before it runs.")

    edited = {}
    invalid = False

    for i, action in enumerate(pending['actions']):
        with st.container(border=True):
            st.markdown(f"**{action['tool']}**")
            raw = st.text_area(
                "Arguments — edit before approving if you want to change them",
                value=json.dumps(action['arguments'], indent=2),
                key=f"args_{pending['thread_id']}_{i}",
                height=200,
            )
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                st.error(f"Not valid JSON: {e}")
                invalid = True
                continue

            if not isinstance(parsed, dict):
                st.error("Arguments must be a JSON object, e.g. {\"query\": \"...\"}")
                invalid = True
                continue

            edited[action['tool_call_id']] = parsed

            gaps = check_args(action['tool'], parsed)
            if gaps:
                st.error(f"Missing required: {', '.join(gaps)}")
                invalid = True

    approve_col, cancel_col = st.columns(2)

    with approve_col:
        if st.button('Approve', type='primary', use_container_width=True,
                     disabled=invalid):
            resume({cid: {'decision': 'approve', 'arguments': args}
                    for cid, args in edited.items()}, pending)

    with cancel_col:
        if st.button('Cancel', use_container_width=True):
            resume({a['tool_call_id']: {'decision': 'cancel'}
                    for a in pending['actions']}, pending)


# ---------------------------------------------------------------- chat input
# Disabled while a turn is parked -- a thread holds one interrupt, and a
# second message would orphan the first.
user_input = st.chat_input(
    'Waiting for your approval above...' if pending else 'Type a message...',
    disabled=bool(pending),
)

if user_input:
    if not st.session_state.chat_id:
        st.session_state.chat_id = requests.post(URL + '/new_chat').json()

    with st.spinner('Thinking...'):
        r = requests.post(URL + '/chat', json={
            'user_input': user_input,
            'chat_id': st.session_state.chat_id,
        })

    if r.status_code != 200 or not r.text:
        st.error(f"Backend error ({r.status_code}). Check the uvicorn console.")
        st.code(r.text[:1000] or "(empty response)")
        st.stop()

    handle(r.json(), user_input)
    st.rerun()