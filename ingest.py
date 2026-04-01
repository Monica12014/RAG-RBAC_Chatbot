# ingest.py - Reads PDFs and stores them in Pinecone

import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

# Load API keys from .env file
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")


def create_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing_indexes = [index.name for index in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index: {INDEX_NAME}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print("Index created successfully!")
    else:
        print(f"Index {INDEX_NAME} already exists.")


def ingest_pdf(pdf_path: str, role: str):
    print(f"Loading PDF: {pdf_path}")
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    print(f"Loaded {len(documents)} pages")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")

    for chunk in chunks:
        chunk.metadata["role"] = role

    print(f"Storing in Pinecone under namespace: {role}")
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=INDEX_NAME,
        namespace=role
    )

    print(f"Successfully ingested {pdf_path} for role: {role}")


if __name__ == "__main__":
    create_pinecone_index()
    ingest_pdf("uploads/walmart_2024.pdf", "walmart")
    ingest_pdf("uploads/tesla_2024.pdf", "tesla")
    print("All documents ingested successfully!")


