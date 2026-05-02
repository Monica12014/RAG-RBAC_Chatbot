# RAG RBAC Chatbot — Architecture

## System Overview

```mermaid
graph TB
    subgraph User["User Layer"]
        Browser["Browser\nhttp://localhost:8501"]
    end

    subgraph App["Application Layer (Streamlit)"]
        UI["app.py\nStreamlit UI"]
        Auth["auth.py\nAuthentication & RBAC"]
        Ingest["ingest.py\nDocument Ingestion"]
    end

    subgraph External["External Services"]
        OpenAI_Embed["OpenAI\ntext-embedding-ada-002"]
        OpenAI_LLM["OpenAI\nGPT-3.5-turbo"]
        Pinecone["Pinecone\nVector DB (Serverless)"]
    end

    subgraph Namespaces["Pinecone Namespaces (RBAC Isolation)"]
        NS_walmart["walmart"]
        NS_tesla["tesla"]
        NS_amazon["amazon"]
        NS_google["google"]
        NS_microsoft["microsoft"]
    end

    subgraph Docs["Document Storage"]
        PDF1["walmart_2024.pdf"]
        PDF2["amazon_2024.pdf"]
        PDF3["google_2024.pdf"]
        PDF4["tesla_2024.pdf"]
    end

    Browser --> UI
    UI --> Auth
    UI --> OpenAI_Embed
    UI --> OpenAI_LLM
    UI --> Pinecone
    Auth --> UI

    Ingest --> OpenAI_Embed
    Ingest --> Pinecone
    Docs --> Ingest

    Pinecone --> NS_walmart
    Pinecone --> NS_tesla
    Pinecone --> NS_amazon
    Pinecone --> NS_google
    Pinecone --> NS_microsoft
```

---

## Authentication & Role-Based Access Control

```mermaid
flowchart TD
    Start([User visits app]) --> CheckSession{Logged in?}

    CheckSession -- No --> LoginForm["Show Login Form\nusername + password"]
    LoginForm --> Creds["auth.login()\nValidate credentials"]
    Creds -- Invalid --> LoginForm
    Creds -- Valid --> GetNS["auth.get_allowed_namespace(role)\nMap role → namespace"]
    GetNS --> StoreSession["Store in session_state\nlogged_in, role, namespace"]
    StoreSession --> ChatUI

    CheckSession -- Yes --> ChatUI["Show Chat Interface"]

    subgraph RBAC["Namespace Mapping"]
        R1["role: walmart  → namespace: walmart"]
        R2["role: tesla    → namespace: tesla"]
        R3["role: amazon   → namespace: amazon"]
        R4["role: google   → namespace: google"]
        R5["role: microsoft→ namespace: microsoft"]
        R6["role: admin    → namespace: None (all)"]
    end

    GetNS -.-> RBAC
```

---

## RAG Query Pipeline

```mermaid
sequenceDiagram
    actor User
    participant UI as app.py (Streamlit)
    participant OAI_E as OpenAI Embeddings
    participant PC as Pinecone
    participant OAI_L as OpenAI GPT-3.5-turbo

    User->>UI: Submits question
    UI->>UI: Read namespace from session_state

    alt Regular user (e.g. walmart)
        UI->>OAI_E: Embed question (text-embedding-ada-002)
        OAI_E-->>UI: 1536-dim vector
        UI->>PC: similarity_search(vector, namespace="walmart", k=4)
        PC-->>UI: Top 4 matching chunks
    else Admin user
        loop For each namespace
            UI->>OAI_E: Embed question
            OAI_E-->>UI: 1536-dim vector
            UI->>PC: similarity_search(vector, namespace=X, k=2)
            PC-->>UI: Top 2 chunks from namespace X
        end
        UI->>UI: Combine all results
    end

    UI->>UI: Build context from chunks + last 6 chat messages
    UI->>OAI_L: system_prompt + context + question
    OAI_L-->>UI: Generated answer
    UI->>UI: Append to chat_history
    UI->>User: Display answer + source documents
```

---

## Document Ingestion Pipeline

```mermaid
flowchart LR
    subgraph Input["Input"]
        Files["uploads/\n*.pdf  *.docx"]
    end

    subgraph Processing["ingest.py"]
        Detect["Auto-detect files\n& extract role\nfrom filename"]
        Load["Load document\nPyPDFLoader\nDocx2txtLoader"]
        Chunk["Split into chunks\nsize=1000 chars\noverlap=200 chars"]
        Meta["Add metadata\nrole, source_file, page"]
        Embed["Embed chunks\nOpenAI ada-002\n→ 1536-dim vectors"]
    end

    subgraph Storage["Pinecone Index: rag-rbac-index"]
        direction TB
        Index["Serverless Index\nAWS us-east-1\ncosine similarity"]
        NS["Namespace = role\ne.g. 'walmart'"]
        Index --> NS
    end

    Files --> Detect --> Load --> Chunk --> Meta --> Embed --> Storage
```

---

## Component Breakdown

```mermaid
graph LR
    subgraph app.py
        Session["Session State\nlogged_in\nrole\nnamespace\nchat_history"]
        GetAnswer["get_answer()\nRAG orchestrator"]
        LoginUI["Login UI"]
        ChatUI["Chat UI"]
        AdminUI["Admin Panel\nadd/delete users"]
    end

    subgraph auth.py
        Login["login()"]
        Namespace["get_allowed_namespace()"]
        AddUser["add_user()"]
        DelUser["delete_user()"]
        GetUsers["get_all_users()"]
        UserDB["In-memory users dict\nusername → password + role"]
    end

    subgraph ingest.py
        CreateIndex["create_pinecone_index()"]
        LoadDoc["load_document()"]
        IngestOne["ingest_document()"]
        IngestAll["ingest_all_uploads()"]
    end

    LoginUI --> Login
    Login --> Namespace
    Namespace --> Session
    Session --> GetAnswer
    AdminUI --> AddUser & DelUser & GetUsers
    AddUser & DelUser & GetUsers --> UserDB

    IngestAll --> IngestOne
    IngestOne --> LoadDoc
    IngestOne --> CreateIndex
```

---

## Data Model

```mermaid
erDiagram
    USER {
        string username PK
        string password
        string role
    }

    ROLE {
        string name PK
        string namespace
    }

    PINECONE_NAMESPACE {
        string name PK
        string index
    }

    VECTOR_CHUNK {
        string id PK
        float[] embedding
        string content
        string role
        string source_file
        int page
    }

    DOCUMENT {
        string filename PK
        string role
        string format
    }

    USER }o--|| ROLE : "has"
    ROLE ||--|| PINECONE_NAMESPACE : "maps to"
    PINECONE_NAMESPACE ||--|{ VECTOR_CHUNK : "contains"
    DOCUMENT ||--|{ VECTOR_CHUNK : "chunked into"
```

---

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | Streamlit | Web UI, session management |
| Auth | Python dict (auth.py) | User store, RBAC logic |
| Embeddings | OpenAI text-embedding-ada-002 | Convert text → 1536-dim vectors |
| LLM | OpenAI GPT-3.5-turbo (temp=0) | Answer generation |
| Vector DB | Pinecone Serverless (AWS us-east-1) | Semantic search with namespace isolation |
| Doc Loading | PyPDFLoader, Docx2txtLoader | Parse PDFs and DOCX files |
| Orchestration | LangChain | Chains embeddings, retrieval, and LLM calls |
| Config | python-dotenv | Load API keys from `.env` |
