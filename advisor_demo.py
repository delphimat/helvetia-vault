import os
import sys
import time
from dotenv import load_dotenv
from pymongo import MongoClient
import voyageai
from openai import OpenAI

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not MONGODB_URI or not VOYAGE_API_KEY or not OPENAI_API_KEY:
    print("❌ ERROR: MONGODB_URI, VOYAGE_API_KEY, and OPENAI_API_KEY must be set in your .env file.")
    sys.exit(1)

# Initialize clients
try:
    db_client = MongoClient(MONGODB_URI)
    voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    print(f"❌ Initialization error: {e}")
    sys.exit(1)

# Database and collection
db = db_client["wealth_management"]
knowledge_base = db["knowledge_base"]

def run_rag_pipeline(question: str):
    print("\n" + "="*70)
    print(" 🤖 PROJECT HELVETIA ADVISOR - VECTOR SEARCH & RAG DEMO ")
    print("="*70)
    print(f"\nUser Question: \"{question}\"")

    print("\n🧠 Step 1: Converting the question into a Vector Embedding...")
    try:
        # Generate embedding using the same model we used to embed the documents
        result = voyage_client.embed(
            texts=[question],
            model="voyage-3-lite"
        )
        query_embedding = result.embeddings[0]
        print(f"✅ Generated a 512-dimensional vector using Voyage AI.")

    except Exception as e:
        print(f"❌ Error generating embedding for the query: {e}")
        sys.exit(1)

    print("\n🔎 Step 2: Querying MongoDB Atlas via $vectorSearch...")
    try:
        # Define the Atlas Vector Search Aggregation Pipeline
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",      # The name of the index we created in setup
                    "path": "embedding",          # The field containing the document vectors
                    "queryVector": query_embedding, # The vector we just generated for the question
                    "numCandidates": 10,          # Number of documents to pre-filter
                    "limit": 3                    # Number of documents to return to the application
                }
            },
            {
                # Project only the fields we need, dropping the heavy vector field to save bandwidth
                "$project": {
                    "_id": 0,
                    "title": 1,
                    "category": 1,
                    "content": 1,
                    "score": {"$meta": "vectorSearchScore"} # Retrieve the similarity score
                }
            }
        ]

        # Execute the pipeline
        retrieved_docs = list(knowledge_base.aggregate(pipeline))

        if not retrieved_docs:
            print("⚠️  No documents found! Ensure setup_knowledge_base.py was run and the vector index has finished building (can take 2-3 mins).")
            sys.exit(1)

        print(f"✅ Retrieved top {len(retrieved_docs)} contextually relevant documents from Atlas.")

        # Display the context retrieved
        print("\n--- Retrieved Context Snippets ---")
        context_text = ""
        for i, doc in enumerate(retrieved_docs, 1):
            score = doc.get("score", 0.0)
            print(f"  {i}. [Score: {score:.4f}] {doc.get('title')} ({doc.get('category')})")
            context_text += f"\nDocument {i} ({doc.get('title')}):\n{doc.get('content')}\n"

    except Exception as e:
        print(f"❌ Error executing Atlas Vector Search: {e}")
        print("\nEnsure the 'vector_index' is fully built in the Atlas UI under Search -> Vector Search.")
        sys.exit(1)

    print("\n💬 Step 3: Generating summarized answer using OpenAI (gpt-4o-mini)...")
    try:
        # Construct the prompt for the LLM, combining the user's question with our MongoDB context
        system_prompt = (
            "You are a Senior Financial Advisor Assistant for Project Helvetia Vault. "
            "You must answer the user's question using ONLY the provided context documents. "
            "If the context does not contain the answer, say 'I cannot answer this based on the provided regulatory documents.' "
            "Keep your answer concise, professional, and directly address the question."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Context Information:\n{context_text}\n\nQuestion: {question}"}
        ]

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.3, # Low temperature for more factual, less creative responses
            max_tokens=300
        )

        answer = response.choices[0].message.content
        print("✅ OpenAI generation complete.")

    except Exception as e:
        print(f"❌ Error generating response from OpenAI: {e}")
        sys.exit(1)

    print("\n" + "="*70)
    print(" 💡 FINAL ADVISOR RESPONSE ")
    print("="*70)
    print(f"\n{answer}\n")
    print("="*70 + "\n")

if __name__ == "__main__":
    # Hardcoded test question to demonstrate RAG capabilities regarding the mock data
    test_question = "What are the rules regarding high-risk client portfolios? Are there any exceptions for cryptocurrency?"

    run_rag_pipeline(test_question)
