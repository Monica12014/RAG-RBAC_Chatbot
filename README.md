# 🤖 RAG Chatbot with Role-Based Access Control (RBAC)

A production-grade AI-powered document assistant that uses **Retrieval-Augmented Generation (RAG)** with **Role-Based Access Control (RBAC)** to ensure users can only access documents they are authorized to view.

---

## 🎯 Business Value

Enterprise organizations deal with sensitive documents across multiple departments and clients. This system solves a critical problem: **how do you let employees query documents using AI without exposing confidential information to unauthorized users?**

- A **Walmart analyst** can query Walmart's financials but cannot access Tesla's data
- A **Tesla analyst** can query Tesla's documents but cannot access Amazon's data
- An **Admin** has full access to all company documents
- All access is enforced automatically at the vector database level

---

## 🏗️ Architecture
```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│                  (Streamlit Web App)                     │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                 Authentication Layer                     │
│              (auth.py - RBAC System)                     │
│         Username → Password → Role → Namespace           │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                  RAG Pipeline (app.py)                   │
│                                                          │
│  User Question → OpenAI Embeddings → Pinecone Search     │
│       → Retrieve Top Chunks → GPT-3.5 → Answer          │
└──────────┬──────────────────────────┬───────────────────┘
           │                          │
           ▼                          ▼
┌─────────────────┐        ┌─────────────────────────────┐
│  Pinecone Index  │        │        OpenAI API            │
│                  │        │                              │
│ Namespace:       │        │  - text-embedding-ada-002    │
│  - walmart       │        │    (embeddings)              │
│  - tesla         │        │  - gpt-3.5-turbo             │
│  - amazon        │        │    (answer generation)       │
│  - google        │        └─────────────────────────────┘
│  - microsoft     │
└─────────────────┘
           ▲
           │
┌─────────────────────────────────────────────────────────┐
│               Document Ingestion Pipeline                │
│                    (ingest.py)                           │
│                                                          │
│  PDF/DOCX → Load → Split Chunks → Embed → Store         │
│  with role metadata in separate Pinecone namespaces      │
└─────────────────────────────────────────────────────────┘
```

---

## 🔐 How RBAC Works

Each user is assigned a **role** which maps to a **Pinecone namespace**:

| Username | Password | Role | Document Access |
|----------|----------|------|----------------|
| walmart_user | walmart@123 | walmart | Walmart docs only |
| tesla_user | tesla@123 | tesla | Tesla docs only |
| amazon_user | amazon@123 | amazon | Amazon docs only |
| google_user | google@123 | google | Google docs only |
| microsoft_user | microsoft@123 | microsoft | Microsoft docs only |
| admin | admin@123 | admin | ALL documents |

When a user logs in, their queries are **scoped to their namespace only** in Pinecone. This means even if someone guesses another company's questions, they get no data back.

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| LLM | OpenAI GPT-3.5-turbo |
| Embeddings | OpenAI text-embedding-ada-002 |
| Vector Database | Pinecone |
| AI Orchestration | LangChain |
| Document Loading | PyPDFLoader, Docx2txtLoader |
| Authentication | Custom RBAC with JSON store |
| Language | Python 3.13 |

---

## 📁 Project Structure
```
rag-rbac-chatbot/
├── app.py              # Main Streamlit application & RAG pipeline
├── auth.py             # Authentication & RBAC logic
├── ingest.py           # Document ingestion pipeline
├── users.json          # User store (auto-managed)
├── requirements.txt    # Python dependencies
├── .env                # API keys (not committed to GitHub)
├── .env.example        # Example env file for setup
├── uploads/            # Place PDF/DOCX files here
│   ├── walmart_2024.pdf
│   ├── tesla_2024.pdf
│   └── ...
└── data/               # Additional data storage
```

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/Lokeshk94/rag-rbac-chatbot.git
cd rag-rbac-chatbot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Create a `.env` file in the root directory:
```
OPENAI_API_KEY=your_openai_api_key
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_INDEX_NAME=rag-rbac-index
```

### 4. Add your documents
Place PDF or DOCX files in the `uploads/` folder following this naming convention:
```
companyname_year.pdf   →  walmart_2024.pdf
companyname_year.docx  →  microsoft_2024.docx
```

### 5. Ingest documents into Pinecone
```bash
# Ingest all documents at once
python ingest.py

# Or ingest a single document
python ingest.py uploads/walmart_2024.pdf walmart
```

### 6. Run the application
```bash
streamlit run app.py
```

---

## 💡 Key Features

- **🔐 Role-Based Access Control** — Users can only query their authorized documents
- **📄 Multi-format Support** — Handles both PDF and DOCX files
- **💬 Conversational Memory** — Maintains context across multiple questions
- **📚 Source Citations** — Shows which document chunks were used for each answer
- **👤 Admin Panel** — Add/delete users and view all users without touching code
- **🏢 Multi-tenant** — Supports unlimited companies/namespaces
- **⚡ Scalable** — Built on enterprise-grade Pinecone vector database

---

## 📊 Use Cases

- **Financial Analysis** — Query annual reports and financial statements
- **Legal Document Review** — Search contracts and compliance documents
- **Enterprise Knowledge Base** — Internal policy and procedure documents
- **Competitive Intelligence** — Separate access for different business units

---

## 🔧 Adding New Companies

1. Download the company's annual report (PDF or DOCX)
2. Name it `companyname_year.pdf` and place in `uploads/`
3. Run: `python ingest.py uploads/companyname_year.pdf companyname`
4. Log in as admin and add a new user via the Admin Panel
5. Done! No code changes needed.

---

## 📝 Environment Variables

| Variable | Description |
|----------|-------------|
| OPENAI_API_KEY | Your OpenAI API key |
| PINECONE_API_KEY | Your Pinecone API key |
| PINECONE_INDEX_NAME | Name of your Pinecone index |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

MIT License — feel free to use this project for learning and development.
