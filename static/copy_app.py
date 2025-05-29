from flask import Flask ,render_template , jsonify , request 
import requests
from src.helper import downloadHuggingFaceEmbedding , generate_qrcode , store_chat_history ,    update_input
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.prompts import ChatPromptTemplate
from langchain_pinecone import PineconeVectorStore
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv 
from src.prompt import systemPrompt , systemAnalizePrompt ,systemAnalyzeUserPrompt
from src.predictions.seat_viewing_predition import seat_view_predition 
from src.predictions.customer_selected_seat import customer_selected_seat_plan
from src.predictions.customer_predition import buying_predition , detect_from_destaination
from src.custom_knowledge import response_selected

import os 

app = Flask(__name__) 

load_dotenv() 

#storing the env variable 
index_name = os.environ.get("VECTOR_INDEX") 
PINECONE_API_KEY= os.environ.get('PINECONE_API')
GROQ_API_KEY=os.environ.get('GROQ_API_KEY')
MODEL_NAME=os.environ.get('MODEL_NAME')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY

# Initialize the LLM
llm = ChatGroq(
    model= MODEL_NAME,
    temperature=0.0,
    max_retries=2,
)

# Dowining the HugginFace
embeddings = downloadHuggingFaceEmbedding() 

docsearch  = PineconeVectorStore.from_existing_index(
    index_name =  index_name,
    embedding = embeddings
)

retriver = docsearch.as_retriever(search_type="similarity" , search_kwargs={'k' : 1 }) 

prompt = ChatPromptTemplate.from_messages(
            [
                ("system", systemPrompt),
                ("human", "{input}")
            ]
        )
questionAnswerChain = create_stuff_documents_chain(llm, prompt)
ragChain = create_retrieval_chain(retriver, questionAnswerChain)


@app.route('/')
def index() : 
    return render_template('index.html')
    

@app.route('/get', methods=["GET", "POST"])
def chat():
    input = request.form.get("msg") or request.json.get("msg") or request.args.get("msg") 
    initState = int( request.form.get("initState") or request.json.get("initState") or request.args.get("initState") )
    avaliableSeats =  request.form.get("avaliable_seats") or request.json.get("avaliable_seats") or request.args.get("avaliable_seats") 

    if not input:
        return jsonify({"error": "No message received"}), 400

    input = update_input(input)
    
    if seat_view_predition(input) and initState == 2:
        response = {} 
        requestUrl = "http://localhost:8000/bus/seat_plan/226/149665?departure_date=04-04-2025&adult=1&is_foreigner=false&type=bus&passenger_type=male"
        rawData = requests.get(requestUrl)
        data = rawData.json() 
        response['answer'] = data['seat_plan']
        response['init_state'] = 3
        response['info'] = """You can hold a seat for only **5 minutes**.  
        The seat plan is updated **live every minute** to reflect real-time availability."""
        
    elif  initState ==  3 :
        response = {}
        if customer_selected_seat_plan(input ,avaliableSeats ) :
            response = {}
            data = "https://your-payment-link.com/order/12345"
            response['init_state'] = 6
            response['answer'] = generate_qrcode(data)
            response['info'] = """Please scan the QR code to complete your booking.  
            Once scanned, your booking will be saved and can be viewed later on the **History** page."""

        else :
            response['answer'] = response_selected(input , avaliableSeats)
            response['init_state'] =3
            response['info'] = ""            
    else : 
        # if not detect_from_destaination(input):
        #     input += "from yangon"
        response = ragChain.invoke({"input": input})  
        response['init_state'] = 2
        response['info'] = ""
        retrieved_documents = retriver.invoke(input)
        print(retrieved_documents)
        # unique_ids = []
        # if retrieved_documents : 
        #     unique_ids = [doc.metadata['unique_id'] for doc in retrieved_documents]
        # else :
        # unique_ids[0] = 0 
        # store_chat_history(1 , response['answer'] , input , unique_ids[0] ) 
    if 'answer' in response:
        return jsonify({"answer": response['answer'] , "init_state" : response['init_state'] , 'info' : response['info']})
    else:
        return jsonify({"error": "No answer found"}), 500

if __name__ == '__main__' : 
    app.run(host="0.0.0.0" , port = 8080 , debug= True) 
    # retrieved_documents = retriver.invoke(input)
        # print(retrieved_documents)
        # unique_ids = []
        # if retrieved_documents : 
        #     unique_ids = [doc.metadata['unique_id'] for doc in retrieved_documents]
        # else :
        # unique_ids[0] = 0 
        # store_chat_history(1 , response['answer'] , input , unique_ids[0] ) 
        
        
        # print(avaliableSeats)
        # if customer_selected_seat_plan(input ,avaliableSeats ) :
        
        #     response['info'] = """Please scan the QR code to complete your booking.  
        #     Once scanned, your booking will be saved and can be viewed later on the **History** page."""
        # else :