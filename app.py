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
from deep_translator.exceptions import RequestError, NotValidPayload, TranslationNotFound
# from langchain.embeddings import OpenAIEmbeddings
from src.predictions.confimation import analyze_input
from dateutil import parser 
from src.predictions.get_avaliable_seat import customDataRetrieval
from src.helper import downloadHuggingFaceEmbedding
import openai
import uuid

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
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
# openai.api_key=OPENAI_API_KEY

openai.OpenAI(api_key=OPENAI_API_KEY)

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

retriver = docsearch.as_retriever(  
    search_type="similarity",
    search_kwargs={'k': 4}
) 

def extract_jj_code(text):
    match = re.search(r"JJ[a-zA-Z0-9]{5}", text)
    return match.group(0) if match else None

def get_custom_unique_id(doc):
    return doc.get("metadata", {}).get("custom_unique_id")

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
    documents = []
    return render_template('index.html', documents=documents)
    

@app.route('/get', methods=["GET", "POST"])
def chat():
    documents = []
    input = request.form.get("msg") or request.json.get("msg") or request.args.get("msg") 
    initState = int( request.form.get("initState") or request.json.get("initState") or request.args.get("initState") )
    avaliableSeats =  request.form.get("avaliable_seats") or request.json.get("avaliable_seats") or request.args.get("avaliable_seats") 
    uniqueId =  request.form.get("uniqueId") or request.json.get("uniqueId") or request.args.get("uniqueId") 
    selectedSeatNo =  request.form.get("selectedSeatNo") or request.json.get("selectedSeatNo") or request.args.get("selectedSeatNo") 
    selectedSeatId =  request.form.get("selectedSeatId") or request.json.get("selectedSeatId") or request.args.get("selectedSeatId") 
    perviousInput =  request.form.get("perviousInput") or request.json.get("perviousInput") or request.args.get("perviousInput") 
    travel_date =  request.form.get("travelDate") or request.json.get("travelDate") or request.args.get("travelDate") 
    boarding_point =  request.form.get("boardingPoint") or request.json.get("boardingPoint") or request.args.get("boardingPoint") 
    dropping_point =  request.form.get("droppingPoint") or request.json.get("droppingPoint") or request.args.get("droppingPoint") 
    documents =  request.form.get("selectedDocs") or request.json.get("selectedDocs") or request.args.get("selectedDocs") 
    
    if not input:
        return jsonify({"error": "No message received"}), 400
    
    if perviousInput is None:
        perviousInput = ""
        
    if documents:
        code = extract_jj_code(input)
        if code:
            print(code)
            for matching_doc in documents:
                custom_id = get_custom_unique_id(matching_doc)
                print('matched dcu')
                if custom_id == code:
                    print('code')
                    data = matching_doc["metadata"].get('unique_id', '')
                    travel_date = matching_doc["metadata"].get('travel_date', '')
                    boarding_point = matching_doc["metadata"].get('boarding_point', '')
                    dropping_point = matching_doc["metadata"].get('dropping_point', '')
                    uniqueId = data if data else 0
                    perviousInput = input
                    initState = 2
        else : 
            print('mis matched')

    if  initState == 2:
        prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "{input}")
                ]
            )
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        custom_retriever = customDataRetrieval(uniqueId , travel_date)
        ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
        response = ragChain.invoke({"input": input})
        match = re.search(r'http[s]?://[^\s]+', response['answer'])
        if match:
            url = match.group()
            rawData = requests.get(url)
            data = rawData.json() 
            response['answer'] = data['seat_plan']
            response['init_state'] = 3 
            response['info'] = """
                You can hold a seat for only **15 minutes**. The seat plan is updated **live every minute** to reflect real-time availability.
                Currently, you can select only **one seat** at a time.
                Please note, for now, I assume you are a male passenger.
                This feature is still in development, so some functionality may be limited.
                If you want to select a seat, just type the seat number.
                """

            response['info'] = GoogleTranslator(source='auto', target='my').translate(response['info'])
        else: 
            response = openai.chat.completions.create( 
            model="gpt-4", 
            messages=[
                {
                    "role": "system",
                        "content": "You are a helpful assistant that receives user travel information in the Myanmar language. Your only task is to translate the input into clear, natural English. Do not change the meaning or add extra information. Just translate."
                    } ,
                    {"role": "user", "content": input}
                ]
            )
            input = response.choices[0].message.content  
            prompt = ChatPromptTemplate.from_messages(
                        [
                            ("system", systemPrompt),
                            ("human", "{input}")
                        ]
                    )
            questionAnswerChain = create_stuff_documents_chain(llm, prompt)
            ragChain = create_retrieval_chain(retriver, questionAnswerChain)
            did_replace , status = replace_relative_or_absolute_date(input)
            input = perviousInput + "." + input
            response = ragChain.invoke({"input": input})
            context_docs = response["context"]
            documents = [ {"page_content": doc.page_content, "metadata": doc.metadata } for doc in context_docs ] 
            
            if not context_docs:
                response['init_state'] = 1
            elif "❌ there is no route for that" in response['answer'].lower():
                response['init_state'] = 1
            response['init_state'] = 1
            match = re.search(r'\b(JJ[A-Z]{5})\b', response['answer'])
            bus_unique_id = match.group(1) if match else None
            matching_doc = None
            if bus_unique_id:
                for doc in context_docs:
                    if doc.metadata.get("custom_unique_id") == bus_unique_id:
                        matching_doc = doc
                        break
            response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
            response['info'] = ""
            if matching_doc:
                data = matching_doc.metadata.get('unique_id', '')
                travel_date = matching_doc.metadata.get('travel_date', '')
                boarding_point = matching_doc.metadata.get('boarding_point', '')
                dropping_point = matching_doc.metadata.get('dropping_point', '')
                uniqueId = data if data else 0
                perviousInput = input
                response['init_state'] = 1
            else:
                data = travel_date = boarding_point = dropping_point = uniqueId = ''
                perviousInput = input
                response['init_state'] = 1
            selectedSeatNo = ""
            selectedSeatId = ""
    elif  initState ==  3 :
        perviousInput  = ""
        response = {}
        response['answer'] , value  , key , initState = response_selected(input , avaliableSeats , uniqueId , boarding_point , dropping_point )
        selectedSeatId = value 
        selectedSeatNo = key 
        response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
        response['init_state'] = initState
        
        response['info'] = ""            
    elif  initState ==  4 :
        input = perviousInput + "." + input
        perviousInput = input 
        response  = analyze_input(input , selectedSeatId , uniqueId , selectedSeatNo)
        # response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer']) 
        if response['init_state'] ==  1 : 
            perviousInput = ""
        response['uniqueId'] = uniqueId 
    else : 
        data = input
        response = openai.chat.completions.create( 
            model="gpt-4", 
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that receives user travel information in the Myanmar language. Your only task is to translate the input into clear, natural English. Do not change the meaning or add extra information. Just translate."
                } ,
                {"role": "user", "content": input}
            ]
        )
        input = response.choices[0].message.content  
        prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", systemPrompt),
                        ("human", "{input}")
                    ]
                )
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        ragChain = create_retrieval_chain(retriver, questionAnswerChain)
        did_replace , status = replace_relative_or_absolute_date(input)
        input = perviousInput + "." + input
        response = ragChain.invoke({"input": input})
        context_docs = response["context"]
        documents = [ {"page_content": doc.page_content, "metadata": doc.metadata } for doc in context_docs ] 
        
        if not context_docs:
            response['init_state'] = 1
        elif "❌ there is no route for that" in response['answer'].lower():
            response['init_state'] = 1
        response['init_state'] = 1
        match = re.search(r'\b(JJ[A-Z]{5})\b', response['answer'])
        bus_unique_id = match.group(1) if match else None
        matching_doc = None
        if bus_unique_id:
            for doc in context_docs:
                if doc.metadata.get("custom_unique_id") == bus_unique_id:
                    matching_doc = doc
                    break
        
        pattern = r"JJ[a-zA-Z0-9]{5}"
        bus_ids = re.findall(pattern, response['answer'])

        # Step 2: Replace with safe placeholders
        placeholder_map = {}
        for i, bus_id in enumerate(set(bus_ids)):
            placeholder = f"BUSID{i}"  # Alphanumeric, no special characters
            placeholder_map[placeholder] = bus_id
            response['answer'] = response['answer'].replace(bus_id, placeholder)


        original = response['answer'] 
        try:
            response['answer'] = GoogleTranslator(source='auto', target='my').translate(response['answer'])

        except (RequestError, NotValidPayload, TranslationNotFound) as e:
            print("Translation error:", e)
            response['answer'] =  original
        # Step 4: Replace placeholders back using regex to match partial distortions
        for placeholder, original_id in placeholder_map.items():
            # Replace even if translator adds extra spaces or punctuation
            pattern = re.compile(rf"\b{re.escape(placeholder)}\b", re.IGNORECASE)
            response['answer'] = pattern.sub(original_id, response['answer'])

        response['info'] = ""
        perviousInput = data
        
        if matching_doc:
            data = matching_doc.metadata.get('unique_id', '')
            travel_date = matching_doc.metadata.get('travel_date', '')
            boarding_point = matching_doc.metadata.get('boarding_point', '')
            dropping_point = matching_doc.metadata.get('dropping_point', '')
            uniqueId = data if data else 0
            
            response['init_state'] = 1
        else:
            data = travel_date = boarding_point = dropping_point = uniqueId = ''
            response['init_state'] = 1
        selectedSeatNo = ""
        selectedSeatId = ""
    if 'answer' in response:
        return jsonify({
            "answer": response['answer'],
            "init_state": response['init_state'],
            "selectedSeatNo": selectedSeatNo,
            "selectedSeatId": selectedSeatId,
            "info":  response['info'],
            "uniqueId": uniqueId  ,
            "perviousInput" : perviousInput ,
            "travelDate" : travel_date , 
            "boardingPoint" : boarding_point , 
            "droppingPoint" : dropping_point, 
            "documents" : documents
        })
    else:
        return jsonify({"error": "No answer found"}), 500

if __name__ == '__main__' : 
    app.run(host="0.0.0.0" , port = 8080 , debug= True) 