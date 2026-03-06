import os
import base64

def generate_local_master_key():
    """
    Generates a cryptographically secure 96-byte local master key for
    MongoDB Client-Side Field Level Encryption (CSFLE) and encodes it in base64.
    """
    try:
        # Generate 96 random bytes
        raw_key = os.urandom(96)

        # Encode to base64 so it can be safely stored as a string in .env
        encoded_key = base64.b64encode(raw_key).decode('utf-8')

        print("\n" + "="*60)
        print("🔑 SUCCESS: 96-Byte Local Master Key Generated!")
        print("="*60)
        print("\nPlease copy the following key and add it to your .env file")
        print("as the value for ENCRYPTION_KEY:\n")
        print(f"ENCRYPTION_KEY=\"{encoded_key}\"")
        print("\n" + "="*60)
        print("⚠️  SECURITY WARNING: Keep this key safe. Do not commit it to version control!")
        print("="*60 + "\n")

    except Exception as e:
        print(f"❌ Error generating key: {e}")

if __name__ == "__main__":
    generate_local_master_key()
