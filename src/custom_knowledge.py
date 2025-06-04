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
token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0b2tlbl9jaGlsZF9hY2NvdW50X2lkIjpudWxsLCJzdWIiOjM2MDkwLCJpc3MiOiJodHRwOi8vMTg4LjE2Ni4yMzEuMC9hcGkvbW9iaWxlL3YxL2F1dGhlbnRpY2F0ZSIsImlhdCI6MTc0ODg2NjM3MywiZXhwIjoxNzQ5Mzg0NzczLCJuYmYiOjE3NDg4NjYzNzMsImp0aSI6IkFyTFZyMjJlaW1HbkxnTDEifQ.kFtfSo6K6zuxy_AR28rA9IkclwhFoLCDRDZXenc0zUw"

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
url = "https://myanmarbustickets.com/api/mobile/v1/get-checkout-data"

# Optional payload for POST



load_dotenv() 

GROQ_API_KEY=os.environ.get('GROQ_API_KEY')
MODEL_NAME=os.environ.get('MODEL_NAME')

#stroing to the python evirement 
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

systemPrompt = (
    "You are an assistant for the bus service. "
    "I will provide you with available  seats. "
    "You must handle customer requests based on the provided data. "
    "If a customer selects an unavailable seat, suggest alternative available seats. and do not ask (name ,email , nrc no ... ) ** important ** customer information "
    "If the customer changes their selection to an available seat, proceed with booking. "
    "If the selected seat is available, ask the customer for the following details: " 
    "Provide the dropping and boarding proint that is important"
    "'name', 'email', 'nrc  no (National Registration Card)',  'phone number' , dropping point , boarding point .\n\n"
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

def get_dynamic_seat_data(selectedSeatNo , boarding_point, dropping_point, available_seats = []):
    if available_seats is None:
        available_seats = []
    return {
        "seat_avaliable": f"Customer selected seat Number is {selectedSeatNo}",
        "dropping_point" : f"{dropping_point}" , 
        "boarding_point" : f"{boarding_point}" ,
        "seat_policy": (
            "Your seat has been successfully selected and held for you. "
            "Seats are reserved for up to 15 minutes. "
            "Please proceed to confirm your booking within this time. "
        )
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
    result = {}
    user_input_upper = user_input.upper()

    for seat_code in seat_map:
        pattern = r'\b' + re.escape(seat_code.upper()) + r'\b'
        if re.search(pattern, user_input_upper):
            result[seat_code] = seat_map[seat_code]

    return result


def response_selected(input, available_seats, unique, boarding_point, dropping_point):
    result = get_seat_id_from_input(input, available_seats)
    print(result)
    if result:  
        key = list(result.keys())[0]
        value = result[key]
        seatId = unique.split('/')[1]
        
        payload = {
            "seatId": seatId,
            "citizenType": "local",
            "seatCount": '1',
            "selectedSeats": value,
        }
        # print(payload)
        try:
            response = requests.post(url, headers=headers, json=payload)
            response_data = response.json()
            print(response_data)
            # ✅ Check if the booking was successful
            if response.status_code == 200 and response_data.get("subTotalPrice"):
                seat_data = get_dynamic_seat_data(key ,boarding_point, dropping_point, available_seats)
                retriever = CustomDataRetriever(custom_data=seat_data)
                rag_chain = create_retrieval_chain(retriever, questionAnswerChain)
                rag_response = rag_chain.invoke({"input": input})
                return rag_response["answer"], value, key, 4
            else:
                # 🛑 Server rejected seat selection
                reason = response_data.get("message", "Unknown error")
                print("Seat selection failed:", reason)
        
        except Exception as e:
            print("Error while processing seat selection:", str(e))

    seat_data =  seat_data = {
        "seat_avaliable": ", ".join(available_seats),
        "seat_policy": (
            "We couldn't confirm your seat selection. This might be due to an invalid seat number "
            "or a temporary issue with the booking system. Please review the available seats and try again. "
            "Seats can be held for up to 15 minutes and can be managed from the History page within 30 days."
        )
    }
    retriever = CustomDataRetriever(custom_data=seat_data)
    rag_chain = create_retrieval_chain(retriever, questionAnswerChain)
    response = rag_chain.invoke({"input": input})
    return response["answer"], 0, 0, 3
