# ingest.py - Reads PDFs and DOCX files and stores them in Pinecone

import os
import sys
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
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
    """
    Creates a Pinecone index if it doesn't already exist.
    """
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
        print(f"Index '{INDEX_NAME}' already exists. Skipping creation.")


def load_document(file_path: str):
    """
    Loads a document based on its file type.
    Supports PDF and DOCX files.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        print(f"Loading PDF: {file_path}")
        loader = PyPDFLoader(file_path)
    elif ext in [".docx", ".doc"]:
        print(f"Loading DOCX: {file_path}")
        loader = Docx2txtLoader(file_path)
    else:
        print(f"ERROR: Unsupported file type: {ext}")
        print("Supported formats: .pdf, .docx, .doc")
        return None

    return loader.load()


def ingest_document(file_path: str, role: str):
    """
    Reads a PDF or DOCX file, splits into chunks,
    converts to embeddings and stores in Pinecone.

    file_path: path to the file
    role: which company this belongs to e.g. "walmart", "tesla"
    """
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return

    # Load the document
    documents = load_document(file_path)
    if documents is None:
        return

    print(f"Loaded {len(documents)} pages/sections")

    # Split into smaller chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = splitter.split_documents(documents)
    print(f"Split into {len(chunks)} chunks")

    # Tag each chunk with the role and source file
    for chunk in chunks:
        chunk.metadata["role"] = role
        chunk.metadata["source_file"] = os.path.basename(file_path)

    # Store in Pinecone under the role's namespace
    print(f"Storing in Pinecone under namespace: '{role}'")
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=INDEX_NAME,
        namespace=role
    )

    print(f"Successfully ingested '{file_path}' for role: '{role}'")


def ingest_all_uploads(uploads_folder: str = "uploads"):
    """
    Automatically ingests ALL PDFs and DOCX files in the uploads folder.
    The role is taken from the filename.

    Example:
        walmart_2024.pdf   -> role = "walmart"
        tesla_2024.pdf     -> role = "tesla"
        microsoft_2024.docx -> role = "microsoft"
        amazon_2024.doc    -> role = "amazon"
    """
    if not os.path.exists(uploads_folder):
        print(f"ERROR: uploads folder not found: {uploads_folder}")
        return

    # Find all supported files
    supported_extensions = (".pdf", ".docx", ".doc")
    files = [
        f for f in os.listdir(uploads_folder)
        if f.lower().endswith(supported_extensions)
    ]

    if not files:
        print("No supported files found in uploads folder.")
        print("Supported formats: .pdf, .docx, .doc")
        return

    print(f"Found {len(files)} file(s) in '{uploads_folder}' folder:")
    for f in files:
        print(f"  - {f}")

    for file_name in files:
        # Extract role from filename
        # e.g. "walmart_2024.pdf" -> "walmart"
        # e.g. "microsoft_2024.docx" -> "microsoft"
        role = file_name.split("_")[0].lower()
        file_path = os.path.join(uploads_folder, file_name)
        ingest_document(file_path, role)

    print("\nAll documents ingested successfully!")


if __name__ == "__main__":
    # Always create index first
    create_pinecone_index()

    if len(sys.argv) == 3:
        # Option 1: Ingest a single specific file
        # Usage: python ingest.py uploads/microsoft_2024.docx microsoft
        file_path = sys.argv[1]
        role = sys.argv[2]
        ingest_document(file_path, role)

    elif len(sys.argv) == 1:
        # Option 2: Ingest ALL files in uploads folder automatically
        # Usage: python ingest.py
        print("\nNo arguments provided. Ingesting ALL files in uploads folder...\n")
        ingest_all_uploads("uploads")

    else:
        print("\nUsage:")
        print("  Ingest ALL files:        python ingest.py")
        print("  Ingest single PDF:       python ingest.py uploads/walmart_2024.pdf walmart")
        print("  Ingest single DOCX:      python ingest.py uploads/microsoft_2024.docx microsoft")
