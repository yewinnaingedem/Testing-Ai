from langchain.schema import BaseRetriever
from typing import List, Dict, Optional
from langchain.schema.document import Document
from pydantic import Field
from langchain_groq import ChatGroq
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
import os 
from dotenv import load_dotenv 
import requests
import json

# The API endpoint from Laravel

# Your Bearer token (you probably get this after login)
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl9jaGlsZF9hY2NvdW50X2lkIjpudWxsLCJzdWIiOjU5MCwiaXNzIjoiaHR0cDovLzE4OC4xNjYuMjMxLjAvYXBpL21vYmlsZS92MS9hdXRoZW50aWNhdGUiLCJpYXQiOjE3NDgyNjIxNzgsImV4cCI6MTc0ODc4MDU3OCwibmJmIjoxNzQ4MjYyMTc4LCJqdGkiOiJrVDZsQmRvODJ2MHk3eGpvIn0.Is1dPNkkfus0AhPDTiw_Deft3HTNqmr9w2d9IgXi2GA"

# Headers with Bearer token
import requests
import re 
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
url = "http://188.166.231.0/api/mobile/v1/get-checkout-data"

# Optional payload for POST



load_dotenv() 

GROQ_API_KEY=os.environ.get('GROQ_API_KEY')
MODEL_NAME=os.environ.get('MODEL_NAME')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

systemPrompt = (
    "You are an assistant for the bus service. "
    "I will provide you with available and unavailable seats. "
    "You must handle customer requests based on the provided data. "
    "If a customer selects an unavailable seat, suggest alternative available seats. "
    "If the customer changes their selection to an available seat, proceed with booking. "
    "If the selected seat is available, ask the customer for the following details: "
    "Provide the dropping and boarding proint that is important"
    "'name', 'email', 'dropping location',  'phone number' , dropping point , boarding point .\n\n"
    "{context}"
)


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

def get_dynamic_seat_data(available_seats = []):
    if available_seats is None:
        available_seats = []
    return {
        "seat_avaliable": ", ".join(available_seats),
        "dropping_point" : "ချမ်းမြရွှေပြည်နားဘတ်စ်ကား (MDY)" , 
        "boarding_point" : "အောင်မင်္ဂလာဘတ်စ်ဂါး, အဝေးပြေးလမ်းဂိတ်တံခါး, အမှတ် 3 မထယ်သာ (YGN)" ,
        "seat_policy": "Seats can be held for up to 15 minutes. Bookings can be managed from the History page within 30 days."
    }


class CustomDataRetriever(BaseRetriever):
    custom_data: Dict[str, str] = Field(default_factory=dict)  # Default value
    search_kwargs: Dict = Field(default_factory=dict)  # Required by BaseRetriever

    def __init__(self, custom_data: Optional[Dict[str, str]] = None, **kwargs):
        """Initialize with custom data (can be from API, database, etc.)."""
        super().__init__(search_kwargs={})  # Ensure required fields exist

        self.custom_data = custom_data 

    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Return ALL customer data every time, ignoring the query."""
        return [Document(page_content=f"{key}: {value}") for key, value in self.custom_data.items()]

def get_seat_id_from_input(user_input, seat_map):
    # Regex to match seat codes like A1, B12, K9, etc.
    matches = re.findall(r'\b([A-Ka-k]\d{1,2})\b', user_input)
    result = {}

    for seat_code in matches:
        seat_code = seat_code.upper()
        if seat_code in seat_map:
            result[seat_code] = seat_map[seat_code]

    return result 


def response_selected (input , available_seats ,  unique) :
    result = get_seat_id_from_input(input, available_seats)
    if result:  # checks if dict is not empty
        key = list(result.keys())[0]
        value = result[key]
        seatId = unique.split('/')[1]
        payload = {
            "seatId": seatId,
            "citizenType": "local",
            "seatCount": '1',
            "selectedSeats": value,
        }
        response = requests.post(url, headers=headers , json=payload)
        seat_data = get_dynamic_seat_data(available_seats)
        retriever = CustomDataRetriever(custom_data=seat_data)
        rag_chain = create_retrieval_chain(retriever, questionAnswerChain)
        response = rag_chain.invoke({"input": input})
        return response["answer"] , value , key , 4
    else :
        seat_data = get_dynamic_seat_data(available_seats)
        retriever = CustomDataRetriever(custom_data=seat_data)
        rag_chain = create_retrieval_chain(retriever, questionAnswerChain)
        response = rag_chain.invoke({"input": input})
        return response["answer"] , 0 , 0 ,3 
