import torch

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

from flask import Flask ,render_template , jsonify , request 
import requests
from deep_translator import GoogleTranslator
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv 
from src.prompt import systemPrompt , system_prompt
from src.custom_knowledge import response_selected 
# from langchain.embeddings import OpenAIEmbeddings
from src.predictions.confimation import analyze_input
from dateutil import parser 
from src.predictions.get_avaliable_seat import customDataRetrieval
from src.helper import downloadHuggingFaceEmbedding
# import openai 
from langchain_core.retrievers import BaseRetriever
from typing import List
from datetime import datetime, timedelta
import re
import os 

app = Flask(__name__) 

load_dotenv() 

index_name = os.environ.get("VECTOR_INDEX") 
PINECONE_API_KEY= os.environ.get('PINECONE_API')
GROQ_API_KEY=os.environ.get('GROQ_API_KEY')
MODEL_NAME=os.environ.get('MODEL_NAME')
OPENAI_APi_KEY=os.environ.get('OPENAI_API_KEY')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
# openai.api_key =  OPENAI_APi_KEY

llm = ChatGroq(
    model= MODEL_NAME,
    temperature=0.0,
    max_retries=2,
)
chat_history = []

embeddings = downloadHuggingFaceEmbedding() 

docsearch  = PineconeVectorStore.from_existing_index(
    index_name =  index_name,
    embedding = embeddings
)

retriver = docsearch.as_retriever(search_type="similarity" , search_kwargs={'k' : 1 }) 


def replace_relative_or_absolute_date(sentence, base_date=None):
    if base_date is None:
        base_date = datetime.today()

    keyword_groups = {
        0: ["today", "tonight", "this evening", "this morning"],
        1: ["tomorrow", "tmr", "the next day"],
        -1: ["yesterday", "the previous day"]
    }

    keyword_to_offset = {
        keyword: offset
        for offset, keywords in keyword_groups.items()
        for keyword in keywords
    }

    sorted_keywords = sorted(keyword_to_offset.keys(), key=len, reverse=True)

    replaced = False
    travel_date = None

    for keyword in sorted_keywords:
        pattern = r'\b' + re.escape(keyword) + r'\b'
        match = re.search(pattern, sentence, flags=re.IGNORECASE)
        if match:
            offset = keyword_to_offset[keyword]
            travel_date = (base_date + timedelta(days=offset)).strftime("%Y-%m-%d")
            replacement_text = f"travel date is {travel_date}"
            sentence = re.sub(pattern, replacement_text, sentence, flags=re.IGNORECASE)
            replaced = True
            return sentence, True  
    try:
        date_patterns = re.findall(r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|[A-Za-z]{3,9} \d{1,2},? \d{4})\b', sentence)
        for date_str in date_patterns:
            try:
                parsed_date = parser.parse(date_str, fuzzy=True)
                travel_date = parsed_date.strftime("%Y-%m-%d")
                replacement_text = f"travel date is {travel_date}"
                sentence = sentence.replace(date_str, replacement_text)
                replaced = True
                return sentence,  True
            except Exception:
                continue
    except Exception:
        pass

    return sentence,  replaced

def build_contextual_input(chat_history, current_input, max_turns=3):
    recent_history = chat_history[-max_turns * 2:]  # human + ai
    history_text = "\n".join([f"{role}: {msg}" for role, msg in recent_history])
    return f"{history_text}\nHuman: {current_input}"

@app.route('/')
def index() : 
    return render_template('index.html')
    

@app.route('/get', methods=["GET", "POST"])
def chat():
    input = request.form.get("msg") or request.json.get("msg") or request.args.get("msg") 
    initState = int( request.form.get("initState") or request.json.get("initState") or request.args.get("initState") )
    avaliableSeats =  request.form.get("avaliable_seats") or request.json.get("avaliable_seats") or request.args.get("avaliable_seats") 
    uniqueId =  request.form.get("uniqueId") or request.json.get("uniqueId") or request.args.get("uniqueId") 
    selectedSeatNo =  request.form.get("selectedSeatNo") or request.json.get("selectedSeatNo") or request.args.get("selectedSeatNo") 
    selectedSeatId =  request.form.get("selectedSeatId") or request.json.get("selectedSeatId") or request.args.get("selectedSeatId") 
    perviousInput =  request.form.get("perviousInput") or request.json.get("perviousInput") or request.args.get("perviousInput") 
    
    if not input:
        return jsonify({"error": "No message received"}), 400
    
    if perviousInput is None:
        perviousInput = ""

    input = perviousInput + "." + input


    if  initState == 2:
        prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "{input}")
                ]
            )
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        custom_retriever = customDataRetrieval(uniqueId)
        ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
        response = ragChain.invoke({"input": input})
        match = re.search(r'http[s]?://[^\s]+', response['answer'])
        if match:
            url = match.group()
            rawData = requests.get(url)
            data = rawData.json() 
            response['answer'] = data['seat_plan']
            response['init_state'] = 3 
            response['info'] = """You can hold a seat for only **5 minutes**. The seat plan is updated **live every minute** to reflect real-time availability.
            if you want to selected the seat just type the seat number you can only selected one seat at this movement
            """
            response['info'] = GoogleTranslator(source='auto', target='my').translate(response['info'])
        else: 
            prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", systemPrompt),
                        ("human", "{input}")
                    ]
                )
            questionAnswerChain = create_stuff_documents_chain(llm, prompt)
            ragChain = create_retrieval_chain(retriver, questionAnswerChain)
            input , did_replace = replace_relative_or_absolute_date(input)
            response = ragChain.invoke({"input": input}) 
            response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
            response['init_state'] = 2 if did_replace else 1
            response['info'] = ""
    elif  initState ==  3 :
        response = {}
        response['answer'] , value  , key , initState = response_selected(input , avaliableSeats , uniqueId )
        selectedSeatId = value 
        selectedSeatNo = key 
        response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
        response['init_state'] = initState
        response['info'] = ""            
    elif  initState ==  4 :
        response = analyze_input(input , selectedSeatId , uniqueId , selectedSeatNo)
        response['intiState'] =  1
        response['uniqueId'] = uniqueId
    else : 
        # response = openai.ChatCompletion.create(
        #     model="gpt-4", 
        #     messages=[
        #         {
        #             "role": "system",
        #             "content": "You are a helpful assistant that receives user travel information in the Myanmar language. Your only task is to translate the input into clear, natural English. Do not change the meaning or add extra information. Just translate."
        #         } ,
        #         {"role": "user", "content": input}
        #     ]
        # )
        # input = response['choices'][0]['message']['content'] 
        input = GoogleTranslator(source='auto', target='en').translate(input)
        print(input)
        prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", systemPrompt),
                        ("human", "{input}")
                    ]
                )
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        ragChain = create_retrieval_chain(retriver, questionAnswerChain)
        input , did_replace = replace_relative_or_absolute_date(input)
        response = ragChain.invoke({"input": input }) 
        context_docs = response["context"]
        response['init_state'] = 2 if did_replace else 1
        print(context_docs)
        if not context_docs:
            response['init_state'] = 1
        elif "❌ there is no route for that" in response['answer'].lower():
            response['init_state'] = 1
        response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
        response['info'] = ""
        retrieved_docs = retriver.get_relevant_documents(input)
        data = [doc.metadata.get('unique_id', '') for doc in retrieved_docs]
        uniqueId = data[0] 
        selectedSeatNo = ""
        selectedSeatId = ""
        perviousInput = input
    if 'answer' in response:
        return jsonify({
            "answer": response['answer'],
            "init_state": response['init_state'],
            "selectedSeatNo": selectedSeatNo,
            "selectedSeatId": selectedSeatId,
            "info":  response['info'],
            "uniqueId": uniqueId  ,
            "perviousInput" : perviousInput 
        })
    else:
        return jsonify({"error": "No answer found"}), 500

if __name__ == '__main__' : 
    app.run(host="0.0.0.0" , port = 8080 , debug= True) 