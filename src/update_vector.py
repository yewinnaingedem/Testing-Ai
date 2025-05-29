from pinecone import Pinecone
import random 
from dotenv import load_dotenv
import os 
# Initialize Pinecone
load_dotenv()
PINECONE_API_KEY=os.environ.get['PINECONE_API_KEY']
index_name = os.environ.get['index_name']

pc = Pinecone(api_key=PINECONE_API_KEY)  # Replace with your actual Pinecone API key
index = pc.Index(index_name)  # Connect to your Pinecone index
# Fetch the record by unique_id
unique_id = "79368"  # Replace with the actual ID

query_vector = [[random.random() for _ in range(384)]]

query_result = index.query(
    vector=query_vector,
    top_k=1,  
    include_metadata=True,
    filter=  {
        "unique_id": {"$ne": unique_id}, 
    } 
)

print(query_result['matches'][0]['id'])  # This will return the stored record