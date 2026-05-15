import sqlite3
import uuid
from datetime import datetime

def init_db():
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
    message_id  Integer  Primary key Autoincrement,
    chat_id  text,
    role text,
    content text,
    timestamp text,
    FOREIGN KEY (chat_id) REFERENCES chats(chat_id)
    )''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
    id  Integer  Primary key Autoincrement,
    chat_id  text,
    chat_name text,
    created_at text
    )''')
    connection.commit()
    connection.close()

def create_chat():
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    u_id= str(uuid.uuid4())
    cursor.execute('''
    Insert into chats (chat_id,created_at) values(?,?)
                   ''',(u_id,datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
    connection.commit()
    connection.close()
    return u_id

def save_message(chat_id,role,content):
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    cursor.execute('Insert into messages (chat_id,role,content,timestamp) values(?,?,?,?)',(chat_id,role,content,datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")))
    connection.commit()
    connection.close()

def get_messages(chat_id):
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    res=cursor.execute('select * from messages where chat_id = ? order by message_id asc',(chat_id,)).fetchall()
    connection.close()
    return res

def chat_name(chat_id,chat):
    chat=chat[:30]
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    cursor.execute('update chats set chat_name= ? where chat_id=?',(chat,chat_id,))
    connection.commit()
    connection.close()

def get_all_chats():
    connection=sqlite3.connect('chat_memory.db')
    cursor=connection.cursor()
    res=cursor.execute('select distinct chat_name , chat_id from chats order by id desc').fetchall()
    connection.close()
    return res