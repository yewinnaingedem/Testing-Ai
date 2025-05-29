# from langchain_community.embeddings import HuggingFaceEmbeddings 
from langchain_openai import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader , DirectoryLoader 
from langchain.text_splitter import RecursiveCharacterTextSplitter

import mysql.connector
from dotenv import load_dotenv

from langchain.chains.combine_documents import create_stuff_documents_chain
import os 
# import pyidaungsu as pds
from datetime import datetime, timedelta
from flask import  url_for
# import imgkit

load_dotenv() 

dbHost = os.environ.get('DB_HOST')
dbUser = os.environ.get('DB_USER')
dbName = os.environ.get('DB_NAME')
dbPassword = os.environ.get('DB_PASSWORD')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')


def load_pdf_loader (data) : 
    loader = DirectoryLoader(data , glob="*.pdf" , loader_cls=PyPDFLoader )
    documents = loader.load() 
    return documents 


def text_splite (extractedData) :
    text_splitter=RecursiveCharacterTextSplitter(chunk_size = 500 , chunk_overlap=20)
    text_chunk = text_splitter.split_documents(extractedData)
    return text_chunk 

def downloadHuggingFaceEmbedding():
    # embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large" , api_key=OPENAI_API_KEY)
    return embeddings




# db = mysql.connector.connect(
#         host= dbHost,
#         user= dbUser,
#         password=dbPassword,
#         database=dbName
#     )
# cursor = db.cursor()
    

def store_chat_history(user_id, chat_message , user_chat , base_res):
    query = "INSERT INTO chatbot (user_id, chat_history, user_chat , base_res) VALUES (%s, %s , %s , %s)"
    values = (user_id, chat_message , user_chat , base_res)
    cursor.execute(query, values)
    db.commit()
    

def get_latest_chat_history(user_id) :
    query = "SELECT chat_history , user_chat FROM chatbot WHERE user_id = %s ORDER BY created_at DESC LIMIT 1"
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()  # Get the first result (latest one)
    if result:
        return f"Here is the user input {result[1]} and Here is the system response data {result[0]}"  
    else:
        return None 

def is_purchase_intent(user_message):
    buy_keywords = ["buy", "order", "purchase", "get this", "want to get", "checkout"]
    return any(keyword in user_message.lower() for keyword in buy_keywords)

def prompt (llm , prompt) :
    questionAnswerChain = create_stuff_documents_chain(llm, prompt)
    return  questionAnswerChain

# def genearte_seat_plan(filePath):
#     with ope(filePath, 'r') as html_file:
#         html_content = html_file.read()
#     imgkit.from_string(html_content, "output.png")n

def generate_seat_plan_image () :
    seat_plan_url = url_for('static', filename='seat_plan.html')
    iframe_html = f'<iframe src="{seat_plan_url}" width="100%" height="900px" style="border:none;"></iframe>'
    return iframe_html

def is_view_seat_plan(user_message):
    buy_keywords = ["view" , "seat plan"]
    return any(keyword in user_message.lower() for keyword in buy_keywords)

def is_user_selected_seat(user_message):
    buy_keywords = ["A1", "A2", "A3", "E1"]
    return any(keyword.lower() in user_message.lower() for keyword in buy_keywords)
import re