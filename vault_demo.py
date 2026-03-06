import os
import sys
import base64
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.encryption import ClientEncryption
from bson.codec_options import CodecOptions

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
ENCRYPTION_KEY_B64 = os.getenv("ENCRYPTION_KEY")

if not MONGODB_URI or not ENCRYPTION_KEY_B64:
    print("❌ ERROR: MONGODB_URI and ENCRYPTION_KEY must be set in your .env file.")
    print("To generate a key, run `python generate_key.py` and copy the output.")
    sys.exit(1)

# Decode the 96-byte base64-encoded local master key
try:
    local_master_key = base64.b64decode(ENCRYPTION_KEY_B64)
    if len(local_master_key) != 96:
        raise ValueError("Key must be exactly 96 bytes long.")
except Exception as e:
    print(f"❌ ERROR: Invalid ENCRYPTION_KEY format. {e}")
    sys.exit(1)

# Configuration for the Local KMS provider
kms_providers = {
    "local": {
        "key": local_master_key
    }
}

# The namespace where MongoDB will store Data Encryption Keys (DEKs)
key_vault_namespace = "wealth_management.__keyVault"
db_name = "wealth_management"
collection_name = "clients"

def setup_client_encryption():
    """
    1. Ensures a Data Encryption Key (DEK) exists in the __keyVault.
    2. Returns the Base64-encoded UUID of the DEK.
    """
    print("\n🔐 Step 1: Setting up Key Vault & KMS Provider...")
    try:
        # Standard client to interact with the key vault
        standard_client = MongoClient(MONGODB_URI)
        key_vault_db = standard_client[db_name]
        key_vault_coll = key_vault_db["__keyVault"]

        # Ensure a unique index on the keyAltNames field (best practice)
        key_vault_coll.create_index("keyAltNames", unique=True, partialFilterExpression={"keyAltNames": {"$exists": True}})

        # Initialize ClientEncryption object
        client_encryption = ClientEncryption(
            kms_providers,
            key_vault_namespace,
            standard_client,
            CodecOptions(uuid_representation=4)
        )

        # Check if we already have a key for "wealth_management_key"
        existing_key = key_vault_coll.find_one({"keyAltNames": "wealth_management_key"})

        if existing_key:
            dek_id = existing_key["_id"]
            print("✅ Existing Data Encryption Key (DEK) found in __keyVault.")
        else:
            print("⏳ Creating a new Data Encryption Key (DEK)...")
            # Create a new DEK and assign it an alternate name
            dek_id = client_encryption.create_data_key("local", key_alt_names=["wealth_management_key"])
            print("✅ New DEK created successfully.")

        return dek_id

    except Exception as e:
        print(f"❌ Error setting up client encryption: {e}")
        sys.exit(1)

def main():
    # 1. Setup KMS and retrieve the DEK ID
    dek_id = setup_client_encryption()

    print("\n🛡️  Step 2: Defining JSON Schema for Deterministic Encryption...")
    # This schema tells MongoDB exactly which fields to encrypt transparently
    schema_map = {
        f"{db_name}.{collection_name}": {
            "bsonType": "object",
            "encryptMetadata": {
                "keyId": [dek_id]
            },
            "properties": {
                "portfolio_value": {
                    "encrypt": {
                        "bsonType": "double",
                        "algorithm": "AEAD_AES_256_CBC_HMAC_SHA_512-Deterministic"
                    }
                }
            }
        }
    }
    print("✅ JSON Schema mapped: 'portfolio_value' will be deterministically encrypted.")

    # 2. Initialize the Secure MongoClient
    print("\n🚀 Step 3: Initializing Secure MongoClient (AutoEncryption enabled)...")
    try:
        auto_encryption_opts = AutoEncryptionOpts(
            kms_providers=kms_providers,
            key_vault_namespace=key_vault_namespace,
            schema_map=schema_map
        )
        secure_client = MongoClient(MONGODB_URI, auto_encryption_opts=auto_encryption_opts)

        # Clear collection for demo purposes
        secure_client[db_name][collection_name].delete_many({})
        print("✅ Secure MongoClient ready.")

    except Exception as e:
        print(f"❌ Error initializing secure client: {e}")
        sys.exit(1)

    # 3. The Demo Flow
    print("\n" + "="*70)
    print(" 🎬 PROJECT HELVETIA VAULT - CSFLE DEMO STARTING ")
    print("="*70)

    mock_client_doc = {
        "name": "Jean Dupont",
        "risk_tolerance": "Low",
        "portfolio_value": 5000000.00
    }

    print("\n➡️  Inserting mock client data using Secure Client:")
    print(mock_client_doc)

    try:
        secure_client[db_name][collection_name].insert_one(mock_client_doc.copy())
        print("✅ Document securely inserted.")
    except Exception as e:
        print(f"❌ Error during secure insert: {e}")
        sys.exit(1)

    print("\n" + "-"*70)
    print("🕵️  SCENARIO 1: The DBA / Cloud Provider View (No Encryption Keys)")
    print("-"*70)

    try:
        standard_client = MongoClient(MONGODB_URI)
        raw_doc = standard_client[db_name][collection_name].find_one({"name": "Jean Dupont"})
        print("Reading the document from Atlas directly bypassing the application tier...\n")

        print("Result:")
        for key, value in raw_doc.items():
            if key == "portfolio_value":
                print(f"  {key}: 🛑 [BINARY CIPHERTEXT] -> {value}")
            else:
                print(f"  {key}: {value}")

        print("\nNotice how 'portfolio_value' is completely unreadable without the Local Master Key!")
    except Exception as e:
        print(f"❌ Error reading raw document: {e}")

    print("\n" + "-"*70)
    print("✅ SCENARIO 2: The Application View (Keys Present, Transparent Decryption)")
    print("-"*70)

    try:
        decrypted_doc = secure_client[db_name][collection_name].find_one({"name": "Jean Dupont"})
        print("Reading the same document using the properly configured AutoEncryption MongoClient...\n")

        print("Result:")
        for key, value in decrypted_doc.items():
            if key == "portfolio_value":
                print(f"  {key}: 🟢 [DECRYPTED PLAINTEXT] -> {value}")
            else:
                print(f"  {key}: {value}")

        print("\nThe driver automatically fetched the DEK, decrypted the value, and presented standard Python types!")
    except Exception as e:
        print(f"❌ Error reading decrypted document: {e}")

    print("\n" + "="*70)
    print(" 🎉 CSFLE DEMO COMPLETE ")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
