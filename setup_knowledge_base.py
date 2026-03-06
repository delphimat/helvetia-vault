import os
import sys
import time
from dotenv import load_dotenv
from pymongo import MongoClient
import voyageai
from pymongo.operations import SearchIndexModel

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
VOYAGE_API_KEY = os.getenv("VOYAGE_API_KEY")

if not MONGODB_URI or not VOYAGE_API_KEY:
    print("❌ ERROR: MONGODB_URI and VOYAGE_API_KEY must be set in your .env file.")
    sys.exit(1)

# Initialize clients
try:
    db_client = MongoClient(MONGODB_URI)
    voyage_client = voyageai.Client(api_key=VOYAGE_API_KEY)
except Exception as e:
    print(f"❌ Initialization error: {e}")
    sys.exit(1)

# Database and collection
db = db_client["wealth_management"]
knowledge_base = db["knowledge_base"]

# Mock regulatory documents for wealth management
MOCK_DOCUMENTS = [
    {
        "title": "High-Risk Client Portfolio Guidelines",
        "category": "Compliance",
        "content": "All high-risk client portfolios must undergo quarterly audits by the compliance team. Any single asset allocation exceeding 30% of the total portfolio value requires secondary approval from a Managing Director. Cryptocurrency and unregistered securities are strictly prohibited in high-risk portfolios unless the client signs a specialized indemnity waiver (Form HR-99)."
    },
    {
        "title": "Anti-Money Laundering (AML) Reporting Procedures",
        "category": "Regulations",
        "content": "If a transaction exceeds $10,000 USD or the equivalent in foreign currency, an AML report must be filed within 24 hours. Advisors must immediately flag any suspicious structuring (e.g., multiple deposits just under the threshold) for review. Accounts exhibiting suspicious behavior will be temporarily frozen pending an internal investigation."
    },
    {
        "title": "Sustainable Investing (ESG) Mandates",
        "category": "Investment Strategy",
        "content": "For clients electing the 'Sustainable Growth' tier, at least 70% of the portfolio must consist of equities or bonds with an ESG rating of A or higher from recognized rating agencies. Fossil fuel extraction companies and controversial weapons manufacturers are automatically excluded from these portfolios."
    }
]

def setup_knowledge_base():
    """
    1. Generates embeddings for mock documents.
    2. Inserts them into MongoDB.
    3. Programmatically creates an Atlas Vector Search index.
    """
    print("\n🔍 Step 1: Generating embeddings for regulatory documents...")
    try:
        # Extract content to embed
        texts_to_embed = [doc["content"] for doc in MOCK_DOCUMENTS]

        # We use 'voyage-3-lite' as it is fast and cost-effective (the "cheapest" reliable option)
        result = voyage_client.embed(
            texts=texts_to_embed,
            model="voyage-3-lite"
        )
        embeddings = result.embeddings

        # Attach embeddings to documents
        for i, doc in enumerate(MOCK_DOCUMENTS):
            doc["embedding"] = embeddings[i]

        print("✅ Embeddings generated successfully.")

    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        return

    print("\n💾 Step 2: Inserting documents into MongoDB Atlas...")
    try:
        # Clear existing data for a clean run
        knowledge_base.delete_many({})
        knowledge_base.insert_many(MOCK_DOCUMENTS)
        print(f"✅ Inserted {len(MOCK_DOCUMENTS)} documents into 'knowledge_base' collection.")
    except Exception as e:
        print(f"❌ Error inserting documents: {e}")
        return

    print("\n⚙️  Step 3: Creating Atlas Vector Search Index...")
    try:
        # Define the Search Index Model
        # This tells Atlas how to index the 'embedding' field for vector search
        index_definition = {
            "fields": [
                {
                    "type": "vector",
                    "path": "embedding",
                    "numDimensions": 512, # voyage-3-lite uses 512 dimensions
                    "similarity": "cosine"
                }
            ]
        }

        search_index_model = SearchIndexModel(
            definition=index_definition,
            name="vector_index",
            type="vectorSearch"
        )

        # Check if index already exists
        existing_indexes = list(knowledge_base.list_search_indexes())
        if any(idx.get("name") == "vector_index" for idx in existing_indexes):
            print("✅ Atlas Vector Search index 'vector_index' already exists.")
        else:
            print("⏳ Initiating index creation. This happens asynchronously in Atlas...")
            knowledge_base.create_search_index(model=search_index_model)
            print("✅ Index creation requested successfully.")
            print("\n⚠️  NOTE: Atlas Search indexes take a few minutes to build.")
            print("If your advisor_demo.py fails to return results immediately, wait 2-3 minutes and try again.")

    except Exception as e:
        print(f"❌ Error creating Atlas Vector Search index: {e}")
        print("\nIf you receive an error about 'cannot create vectorSearch index', ensure you are connected to a MongoDB Atlas cluster running version 6.0.11+, 7.0.2+, or newer, and that your cluster tier supports Vector Search (M0 free tiers *do* support it, but it requires Atlas).")

if __name__ == "__main__":
    setup_knowledge_base()
    print("\n🎉 Setup complete! You are ready to run advisor_demo.py.\n")
