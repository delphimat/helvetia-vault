import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.encryption_options import AutoEncryptionOpts

# ==========================================
# 1. Configuration & Environment
# ==========================================
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LOCAL_MASTER_KEY = os.getenv("ENCRYPTION_KEY")


# ==========================================
# 2. Pydantic Data Models (Schemas)
# ==========================================
# These enforce strict type-checking for our API requests.

class ClientProfile(BaseModel):
    name: str
    risk_tolerance: str
    portfolio_value: float  # This is the field we will encrypt!


class AdvisorQuery(BaseModel):
    question: str


# ==========================================
# 3. Database & CSFLE Initialization
# ==========================================
# We use FastAPI's lifespan events to cleanly open and close DB connections.

db_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client

    # TODO: Configure the KMS provider (Local for this PoC)
    # TODO: Define the JSON schema to tell MongoDB which fields to encrypt
    # TODO: Initialize MongoClient with AutoEncryptionOpts

    print("Vault Secured: Connected to MongoDB Atlas with CSFLE enabled.")
    yield

    if db_client:
        db_client.close()
        print("Connection closed.")


# ==========================================
# 4. FastAPI Application Setup
# ==========================================
app = FastAPI(
    title="Helvetia Vault API",
    description="Secure Wealth Management Data Layer with CSFLE and RAG",
    version="1.0.0",
    lifespan=lifespan
)


# ==========================================
# 5. API Routes (The Vault & The Advisor)
# ==========================================

@app.post("/api/v1/clients/", tags=["Vault"])
async def create_client(client: ClientProfile):
    """
    Ingests a new client profile. 
    The portfolio_value will be transparently encrypted before leaving this server.
    """
    # TODO: Insert document into MongoDB
    return {"status": "success", "message": "Client encrypted and stored safely."}


@app.get("/api/v1/clients/{client_name}", tags=["Vault"])
async def get_client(client_name: str):
    """
    Retrieves a client profile. 
    The portfolio_value will be transparently decrypted upon retrieval.
    """
    # TODO: Fetch document from MongoDB
    return {"status": "success", "data": "client_data_here"}


@app.post("/api/v1/advisor/ask", tags=["Advisor"])
async def ask_advisor(query: AdvisorQuery):
    """
    RAG Endpoint: Takes a natural language question, embeds it via Voyage AI, 
    searches the MongoDB knowledge base, and returns an LLM-generated answer.
    """
    # TODO: Generate embedding with Voyage AI
    # TODO: Execute $vectorSearch aggregation pipeline
    # TODO: Pass results to OpenAI for final response formulation
    return {"status": "success", "answer": "LLM_response_here"}