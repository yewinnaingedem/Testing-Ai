from langchain.schema import BaseRetriever
from typing import List, Dict, Optional
from langchain.schema.document import Document
from pydantic import Field
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from io import BytesIO
import os 
from dotenv import load_dotenv 
import json
import openai
import qrcode
import base64
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl9jaGlsZF9hY2NvdW50X2lkIjpudWxsLCJzdWIiOjU5MCwiaXNzIjoiaHR0cDovLzE4OC4xNjYuMjMxLjAvYXBpL21vYmlsZS92MS9hdXRoZW50aWNhdGUiLCJpYXQiOjE3NDgyNjIxNzgsImV4cCI6MTc0ODc4MDU3OCwibmJmIjoxNzQ4MjYyMTc4LCJqdGkiOiJrVDZsQmRvODJ2MHk3eGpvIn0.Is1dPNkkfus0AhPDTiw_Deft3HTNqmr9w2d9IgXi2GA"

# Headers with Bearer token
import requests

# Replace with actual values or environment variables
APIKEY = 'u8RNBnbVL6ssZLHAB6N3nbVXtaRimbLz'
APISECRET = 'N3QyymqwAsaLEjAaZwu6BkYEu7B7UXBK'
APPTYPE = 'ticketing'

headers = {
    'X-API-KEY': APIKEY,
    'X-API-SECRET': APISECRET,
    'Accept': 'application/json',
    'X-App-Type': APPTYPE,
    'Authorization': f'Bearer {token}'  # Include if needed
}

# API endpoint
url = "https://myanmarbustickets.com/api/mobile/v1/confirm-booking"




load_dotenv() 

GROQ_API_KEY=os.environ.get('GROQ_API_KEY')
MODEL_NAME=os.environ.get('MODEL_NAME')
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY
openai.api_key=OPENAI_API_KEY

systemPrompt = (
    "You are an assistant for the bus service. "
    "Confrim that user with given information"
    "{context}"
)

def generate_qrcode (data) :     
    qr = qrcode.make(data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    return f'<img src="data:image/png;base64,{qr_base64}" width="300px" height="300px" alt="QR Code">'  


# Initialize the LLM
llm = ChatGroq(
    model= MODEL_NAME,
    temperature=0.0,
    max_retries=2,
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", systemPrompt),
        ("human", "{input}")
    ]
)

questionAnswerChain = create_stuff_documents_chain(llm, prompt)

class CustomDataRetriever(BaseRetriever):
    custom_data: Dict[str, str] = Field(default_factory=dict)
    search_kwargs: Dict = Field(default_factory=dict)

    def __init__(self, custom_data: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(search_kwargs={})

        # Use provided custom_data or fallback to default data
        self.custom_data = custom_data if custom_data is not None else {
            "booking_confirmation": "Customer name Ye Win Naing successfully booked the route from Yangon to Mandalay with ref No: SM-AAA001.",
            "customer_details": "Name: Ye Win Naing, Email: edem@gmail.com, Phone: 091234555, Dropping Point: Mandalay, Starting Point: Aungmingalar Bus Station.",
            "system_policy": "This customer can manage the booking at jjexpress.net using their reference number."
        }

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return [Document(page_content=f"{key}: {value}") for key, value in self.custom_data.items()]
    
def confirmation_response ( too_arg  , uniqueId , selectedSeat , selectedSeatNo) :
    name = too_arg['name']
    email = too_arg['email']
    phone = too_arg['phone']
    dropping_point = too_arg['dropping_point']
    boarding_point = too_arg['boarding_point']
    nrc_no = too_arg['nrc_no']
    seatId = uniqueId.split('/')
    # Optional payload for POST
    payload = {
        "boarding_point": boarding_point ,
        "dropping_point" : dropping_point ,
        "selected_seat": f"'{selectedSeat},'" ,
        "seat_no": f"{selectedSeatNo},", 
        "seat_id": seatId[1] ,
        "service" : 0 ,
        "travel_date" : "2025-02-15" ,
        "adult" : '1' ,
        "type" : 'local' ,
        "payment_method" : "kbz_pay" ,
        "bus_id" : seatId[0] ,
        "guest_name" : name,
        "guest_mobile" : phone ,
        "guest_email" : email ,
        "passenger_name" : name ,
        "passenger_type" : 'male' ,
        "note" : "TT" ,
        "offer_code" : "JJNEW" ,
        "offer_amount" : 0 ,
        "nrc_no" : nrc_no ,
        "ostype" : "mobile" ,
    }
    print(payload)
    response = requests.post(url, headers=headers , json=payload).json()
    print(response)
    if response.get("paymentUrl"):
        customData = {
            f"booking_confirmation": f"Customer name {name} successfully booked the route from Yangon to Mandalay with ref No: {response.get('refCode')}",
            f"customer_details": f"Name: {name}, Email: {email}, Phone: {phone}, Dropping Point: {dropping_point}, Starting Point: {boarding_point} Bus Station.",
            "system_policy": "This customer can manage the booking at jjexpress.net using their reference number.|"
        }
        data = generate_qrcode(response.get('paymentUrl'))
        initState = 1
    else : 
        customData = {
            "booking_failed": f"Booking failed. The seat was already reserved by another customer. {name} could not complete the booking for the route from Yangon to Mandalay.",
            "customer_details": f"Name: {name}, Email: {email}, Phone: {phone}, Dropping Point: {dropping_point}, Starting Point: {boarding_point} Bus Station.",
            "system_policy": "Please try booking again with a different seat. Visit jjexpress.net for availability and support.|"
        }
        initState = 4
        data = ''
    retriever = CustomDataRetriever(custom_data=customData)
    rag_chain = create_retrieval_chain(retriever, questionAnswerChain)
    return rag_chain.invoke({"input": "provid my booking information"}) , initState ,data 
    
function_descriptions = [
    {
        "name": "get_bus_info",
        "description": "Get Bus Route information between two locations",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The user name (Ye Win Naing)",
                },
                "email": {
                    "type": "string",
                    "description": "User Email",
                },
                "nrc_no" : {
                    "type" : "string" ,
                    "description" : "National Registration Card for myanamr example - 12/nrc(n)123456"
                },
                "phone": {
                    "type": "string",
                    "description": "User Phone 0912345678",
                },
                "dropping_point" : {
                    "type": "string",
                    "description": "The dropping point (Mandalay , city...)",
                },
                "boarding_point" : {
                    "type": "string",
                    "description": "The Boarding point (Aungmingalar , city...)",
                },
            },
            "required": ["name", "email" , "phone" , 'dropping_point' , 'boarding_point' , "nrc_no" ],
        },
    }
]

def analyze_input (input , selectedSeat , uniqueId , selectedSeatNo )  : 
    response = openai.chat.completions.create( 
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Analyze the user's input to extract required data: name, email, phone number, dropping point, and boarding point. "
                        "If any of this information is missing, politely ask the user to provide it. "
                        "Note: The user may provide information in plain text or as part of a paragraph. "
                        "Your job is to accurately extract the required details regardless of format and ensure all necessary fields are collected."
                    )
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

    if message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]
        tool_args = json.loads(tool_call.function.arguments)
        response , initState , data = confirmation_response(tool_args , uniqueId , selectedSeat , selectedSeatNo)
        # data = "https://your-payment-link.com/order/12345"
        response['init_state'] = initState
        response['info'] = data
    else:
        response = {}
        response['answer'] = message.content
        response['init_state'] = 4
        response['info'] = ""
    return response        
            
