# Project Helvetia Vault 🏦🇨🇭

**A Secure, FINMA-Compliant Wealth Management Data Layer and AI Advisor**

Helvetia Vault is a Proof of Concept (PoC) designed to demonstrate how Swiss financial institutions can modernize their operational data layer while strictly adhering to data sovereignty and privacy regulations.

It leverages **MongoDB Atlas** as a unified developer data platform to handle highly sensitive Client PII alongside unstructured knowledge bases for Generative AI, completely eliminating the need for fragmented, bolted-on vector databases.

## 🎯 Architectural Objectives

1. **Zero-Trust Data Security (CSFLE):** Demonstrate cryptographic locking of sensitive client data (e.g., Portfolio Values) *before* it leaves the application server. This ensures that even in the event of a compromised DBA account or cloud provider breach, the data remains unreadable ciphertext.
2. **Context-Aware AI (RAG with Voyage AI):** Provide a Retrieval-Augmented Generation (RAG) endpoint for wealth advisors to query internal financial policies. We utilize **Voyage AI** for state-of-the-art, finance-optimized vector embeddings, natively stored and queried via MongoDB Atlas Vector Search.
3. **Operational Simplicity:** Containerized deployment via Docker to showcase rapid time-to-market and CI/CD readiness.

## 🏗️ Technology Stack

* **Database:** MongoDB Atlas (M0/M10 Cluster)
* **Application Framework:** Python 3.11 / FastAPI
* **Encryption:** `pymongo-crypt` (Client-Side Field Level Encryption)
* **Embeddings:** Voyage AI (`voyage-finance-2` or similar model)
* **Deployment:** Docker & Docker Compose

## ⚙️ Core Mechanics

### 1. The Vault (CSFLE)
When a new client profile is ingested via the API, the application uses a Customer Master Key (CMK) to encrypt specific fields (e.g., `portfolio_value`). The MongoDB cluster only ever receives and stores binary ciphertext. The application tier retains the keys, ensuring strict separation of duties and FINMA compliance.

### 2. The Advisor (Vector Search)
Internal regulatory documents are chunked and embedded using Voyage AI. These embeddings are stored in Atlas alongside standard operational data. When an advisor asks a question, the query is embedded via Voyage AI, and an `$vectorSearch` aggregation pipeline retrieves the most relevant policy chunks to ground the LLM's response.

## 🚀 Quickstart Guide

### Prerequisites
* Docker and Docker Compose installed
* MongoDB Atlas Cluster (with Vector Search enabled)
* Voyage AI API Key

### 1. Environment Setup
Clone the repository and create your environment variables:
```bash
cp .env.example .env