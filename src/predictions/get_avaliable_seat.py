from langchain.schema import BaseRetriever, Document
from typing import List, Dict, Optional
from pydantic import Field
import requests
import json

# The API endpoint from Laravel

# Your Bearer token (you probably get this after login)
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
url = "http://188.166.231.0/api/mobile/v1/get-checkout-data"

# Optional payload for POST


# Example GET request


class CustomDataRetrieverForSeatPlan(BaseRetriever):
    custom_data: Dict[str, str] = Field(default_factory=dict)

    def __init__(self, custom_data: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.custom_data = custom_data or {
            "seat_info": (
                "http://188.166.231.0/bus/seat_plan/226/149665?departure_date=04-04-2025&adult=1&is_foreigner=false&type=bus&passenger_type=male"
            )
        }

    def _get_relevant_documents(self, query: str) -> List[Document]:
        return [
            Document(page_content=f"{key}: {value}")
            for key, value in self.custom_data.items()
        ]


def customDataRetrieval(data) -> CustomDataRetrieverForSeatPlan:
    
    custom_data = {
        "seat_info": (
            f"http://188.166.231.0/bus/seat_plan/{data}?departure_date=04-04-2025&adult=1&is_foreigner=false&type=bus&passenger_type=male"
        )
    }
    
    return CustomDataRetrieverForSeatPlan(custom_data=custom_data)
