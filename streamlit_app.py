import streamlit as st
import requests

if 'chat_id' not in st.session_state:
    st.session_state.chat_id = None
if 'messages' not in st.session_state:
    st.session_state.messages=[]
if 'mode' not in st.session_state:
    st.session_state.mode='chat'

url='http://127.0.0.1:8000'
with st.sidebar:
    if st.button('new_chat'):
        st.session_state.chat_id = requests.post(url+"/new_chat").json()
        st.session_state.messages = []
        st.session_state.mode = 'chat'
        st.rerun()
    res=requests.get(url+'/chats').json()
    for name, chat_id in res:
        if st.button(name or "New Chat", key=chat_id):
            st.session_state.chat_id = chat_id
            st.session_state.messages = requests.get(url+f'/messages/{chat_id}').json()
    
    file=st.file_uploader("Upload PDF", type=["pdf"])
    if file:
        st.session_state.mode = 'rag'
        requests.post(url+'/upload_pdf', files={'pdf': file})

for message in st.session_state.messages:
    with st.chat_message(message['role']):
        st.write(message['content'])

user_input=st.chat_input('Type a message...')

if user_input:
    if not st.session_state.chat_id:
        st.session_state.chat_id = requests.post(url+"/new_chat").json()
    with st.spinner('Thinking...'):
        res = requests.post(url+'/chat', json={'user_input': user_input, 'chat_id': st.session_state.chat_id, 'query_type': st.session_state.mode}).json()
    if res.get('structured_output'):
        st.session_state.messages.append({'role': 'user', 'content': user_input})
        st.dataframe(res['structured_output'])
    else:
        st.session_state.messages.extend([
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': res['response']}
        ])
    st.rerun()