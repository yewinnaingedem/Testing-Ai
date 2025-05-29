from src.helper import load_pdf_loader , text_splite , downloadHuggingFaceEmbedding
from pinecone.grpc import PineconeGRPC as Pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
import os 
from dotenv import load_dotenv 
load_dotenv()

PINECONE_API_KEY= os.environ.get('PINECONE_API')

pc = Pinecone(api_key=PINECONE_API_KEY)
index_name = "chatbot"

extractedData = load_pdf_loader(data="Data/")
embeddings = downloadHuggingFaceEmbedding()
txt_chunks = text_splite(extractedData)

pc.create_index(
    name=index_name,
    dimension= 384, # Replace with your model dimensions
    metric="cosine", # Replace with your model metric
    spec=ServerlessSpec(
        cloud="aws",
        region="us-east-1"
    ) 
)

os.environ["PINECONE_API_KEY"] = "pcsk_77r8Kg_GipbZFJXfyyr72tgTHpuJXh1d5ZDuxuShjo9Dp13eGL5sqZJDS1QXrpmh2d219c"


docsearch = PineconeVectorStore.from_documents(
    documents= txt_chunks,
    index_name = index_name,
    embedding= embeddings
)