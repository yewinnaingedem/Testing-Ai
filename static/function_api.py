from langchain.schema import BaseRetriever
from typing import List, Dict, Optional
from langchain.schema.document import Document
from pydantic import Field
from langchain_groq import ChatGroq
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from flask import Flask ,render_template , jsonify , request 
import requests
import os 
import re
import json
import openai
import os
from langchain.chat_models import ChatOpenAI
from src.function_calling_api.get_avaliable_seat import CustomDataRetrieverForSeatPlan
from src.function_calling_api.booking_seat import select_booking
from src.function_calling_api.booking_confirm import get_custmer_info 
from src.function_calling_api.makeing_decission import is_user_interested
from dotenv import load_dotenv 
load_dotenv()
app = Flask(__name__) 

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
systemPrompt = (
    "You are a helpful assistant for a premium bus service JJ EXpress company.\n"
    "You are provided with the latest seat availability and schedule data.\n"
    "Your job is to assist customers in selecting and reserving seats based on the provided data.\n"
    "Always use the available data context to make decisions, and never assume information not given.\n\n"
    "Alway ask the user to would you like to view the seat plan (ထိုင်ခုံ )"
    "Don't forget to answer the price\n"
    "Context:\n"
    "{context}"
)

system_prompt = (
    "You are a helpful assistant for a premium bus service.\n"
    "If the customer is asking to **view the seat plan** or know which seats are available or taken,\n"
    "then show them the seat availability only provided route.\n"
    "If the customer is **not** asking about the seat plan (ထိုင်ခုံ ), just respond with the number '0' — do not answer or explain anything else.\n"
    "respnse based on user input languages"
    "{context}"
)


openai.api_key =  OPENAI_API_KEY
function_descriptions = [
    {
        "name": "get_bus_info",
        "description": "Get Bus Route information between two locations",
        "parameters": {
            "type": "object",
            "properties": {
                "loc_origin": {
                    "type": "string",
                    "description": "The departure bus station",
                },
                "loc_destination": {
                    "type": "string",
                    "description": "The destination bus station, e.g. Mandalay",
                },
                "travel_date" : {
                    "type": "string",
                    "description": "The departure Time",
                }
            },
            "required": ["loc_origin", "loc_destination" , 'travel_date' ],
        },
    }
]

# --------------------------------------------------------------
# User Message
# --------------------------------------------------------------


class CustomDataRetriever(BaseRetriever):
    custom_data: Dict[str, str] = Field(default_factory=dict)
    tool_args: Dict[str, str] = Field(default_factory=dict)
    search_kwargs: Dict = Field(default_factory=dict)

    def __init__(self, tool_args: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(search_kwargs={})
        self.tool_args = tool_args or {}

        origin = self.tool_args.get("loc_origin", "Unknown Origin")
        destination = self.tool_args.get("loc_destination", "Unknown Destination")

        self.custom_data = {
            "bus_info": (
                f"Route from {origin} to {destination}:\n"
                "On May 20, 2025, at 3:00 PM, a first-class express bus will depart from Yangon Central Bus Station "
                "en route to Mandalay, offering a comfortable and efficient travel experience. "
                "Passengers can enjoy premium onboarding services..."
                "\nPrice: 35,000 MMK (local), 50,000 MMK (foreigner)."
            )
        }

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return [
            Document(page_content=f"{key}: {value}")
            for key, value in self.custom_data.items()
        ]
        

# Initialize the LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.0,
    max_retries=2,
)


# llm = ChatOpenAI(
#     model_name="gpt-4",  # or "gpt-4-turbo" or "gpt-3.5-turbo"
#     temperature=0.0,
#     max_retries=2,
# )
def determine_init_state (input) :
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "Your are helpful assistant of jj express Triggers the function call when the user talks about travel, locations, or cities . Uses Yangon as the default origin if the user doesn't provide one . Uses tomorrow as the default travel date if none is specified."
                ),
            },
            { "role": "user", "content": input }
        ],
        tools=[  # 'tools' is correct for GPT-4-turbo
            {
                "type": "function",
                "function": function_descriptions[0]
            }
        ],
        tool_choice="auto"
    )

    # Check if a function was called
    message = response.choices[0].message

    if "tool_calls" in message:
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", systemPrompt),
                ("human", "{input}")
            ]
        )
        # Create the question-answering chain using the LLM and the prompt
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        tool_call = response.choices[0].message.tool_calls[0]
        tool_args = json.loads(tool_call.function.arguments)
        tool_args = json.loads(tool_call["function"]["arguments"])
        custom_retriever = CustomDataRetriever(tool_args=tool_args)
        ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
        response = ragChain.invoke({"input": input})
        response['initSate'] = 2
    else:
        response = {}
        response['answer'] = message["content"] 
        response['initSate'] = 1
    return response 
# Create the prompt template
        
@app.route('/')
def index() : 
    return render_template('index.html')
    

@app.route('/get', methods=["GET", "POST"])
def chat():
    input = request.form.get("msg") or request.json.get("msg") or request.args.get("msg") 
    initState = int( request.form.get("initState") or request.json.get("initState") or request.args.get("initState") )
    # avaliableSeats =  request.form.get("avaliable_seats") or request.json.get("avaliable_seats") or request.args.get("avaliable_seats") 
    
    if not input:
        return jsonify({"error": "No message received"}), 400
    
    if initState == 2 :
        prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    ("human", "{input}")
                ]
            )
            # Create the question-answering chain using the LLM and the prompt
        questionAnswerChain = create_stuff_documents_chain(llm, prompt)
        custom_retriever = CustomDataRetrieverForSeatPlan()
        ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
        response = ragChain.invoke({"input": input})
        match = re.search(r'http[s]?://[^\s]+', response['answer'])
        if match:
            url = match.group()
            rawData = requests.get(url)
            data = rawData.json() 
            response['answer'] = data['seat_plan']
        response['initSate'] = 3
        # print(response.get('answer'))
        if str(response.get('answer')).strip() == '0':
            response = openai.ChatCompletion.create(
                model="gpt-4-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Triggers the function call when the user talks about travel, locations, or cities . Uses Yangon as the default origin if the user doesn't provide one . Uses tomorrow as the default travel date if none is specified."
                        ),
                    },
                    { "role": "user", "content": input }
                ],
                tools=[  # 'tools' is correct for GPT-4-turbo
                    {
                        "type": "function",
                        "function": function_descriptions[0]
                    }
                ],
                tool_choice="auto"
            )

            # Check if a function was called
            message = response.choices[0].message

            if "tool_calls" in message:
                prompt = ChatPromptTemplate.from_messages(
                    [
                        ("system", systemPrompt),
                        ("human", "{input}")
                    ]
                )
                # Create the question-answering chain using the LLM and the prompt
                questionAnswerChain = create_stuff_documents_chain(llm, prompt)
                tool_call = response.choices[0].message.tool_calls[0]
                tool_args = json.loads(tool_call.function.arguments)
                tool_args = json.loads(tool_call["function"]["arguments"])
                custom_retriever = CustomDataRetriever(tool_args=tool_args)
                ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
                response = ragChain.invoke({"input": input})
                response['initSate'] = 2
            else:
                response = {}
                response['answer'] = message["content"] 
                response['initSate'] = 1
    elif initState == 3 :
        response = select_booking(input)
        response['initSate'] = 4
    elif initState == 4 :
        response = get_custmer_info(input)
        response['initSate'] = 4
    else :
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Triggers the function call when the user talks about travel, locations, or cities . Uses Yangon as the default origin if the user doesn't provide one . Uses tomorrow as the default travel date if none is specified."
                    ),
                },
                { "role": "user", "content": input }
            ],
            tools=[  # 'tools' is correct for GPT-4-turbo
                {
                    "type": "function",
                    "function": function_descriptions[0]
                }
            ],
            tool_choice="auto"
        )

        # Check if a function was called
        message = response.choices[0].message

        if "tool_calls" in message:
            prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", systemPrompt),
                    ("human", "{input}")
                ]
            )
            # Create the question-answering chain using the LLM and the prompt
            questionAnswerChain = create_stuff_documents_chain(llm, prompt)
            tool_call = response.choices[0].message.tool_calls[0]
            tool_args = json.loads(tool_call.function.arguments)
            tool_args = json.loads(tool_call["function"]["arguments"])
            custom_retriever = CustomDataRetriever(tool_args=tool_args)
            ragChain = create_retrieval_chain(custom_retriever, questionAnswerChain)
            response = ragChain.invoke({"input": input})
            response['initSate'] = 2
        else:
            response = {}
            response['answer'] = message["content"] 
            response['initSate'] = 1
        print('hello world')
    if 'answer' in response:
        return jsonify({"answer": response['answer'] , "init_state" : response['initSate']  , 'info' : ''})
    else:
        return jsonify({"error": "No answer found"}), 500

if __name__ == '__main__' : 
    app.run(host="0.0.0.0" , port = 8080 , debug= True) 