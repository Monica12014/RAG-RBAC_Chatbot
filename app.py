# app.py - Main chatbot application

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from auth import login, get_allowed_namespace

# Load API keys
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")


def get_qa_chain(namespace: str):
    """
    Creates the AI chat chain for a specific role/namespace.
    This is what actually answers questions using the documents.
    """
    # Set up embeddings - converts questions into vectors for searching
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # Connect to the right namespace in Pinecone based on user role
    vectorstore = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings,
        namespace=namespace,
        pinecone_api_key=PINECONE_API_KEY
    )

    # Set up the AI model
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model="gpt-3.5-turbo",
        temperature=0  # 0 = factual answers, no creativity
    )

    # Memory keeps track of conversation history
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"
    )

    # Create the full RAG chain
    # This combines: search documents -> send to GPT -> get answer
    qa_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(
            search_kwargs={"k": 4}  # fetch top 4 most relevant chunks
        ),
        memory=memory,
        return_source_documents=True
    )

    return qa_chain


# ─── Streamlit UI ────────────────────────────────────────────────────────────

# Page config
st.set_page_config(
    page_title="RAG RBAC Chatbot",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 RAG Chatbot with Role-Based Access Control")

# ─── Login Screen ─────────────────────────────────────────────────────────────

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "role" not in st.session_state:
    st.session_state.role = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None


if not st.session_state.logged_in:
    st.subheader("Please log in to continue")

    col1, col2 = st.columns([1, 2])

    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            role = login(username, password)

            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                namespace = get_allowed_namespace(role)
                st.session_state.namespace = namespace
                st.session_state.qa_chain = get_qa_chain(namespace)
                st.success(f"Welcome! You are logged in as: {role}")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with col2:
        st.info("""
        **Available Test Users:**
        
        | Username | Password | Access |
        |----------|----------|--------|
        | walmart_user | walmart123 | Walmart docs only |
        | tesla_user | tesla123 | Tesla docs only |
        | amazon_user | amazon123 | Amazon docs only |
        | admin | admin123 | All documents |
        """)

# ─── Chat Screen ──────────────────────────────────────────────────────────────

else:
    # Sidebar with user info
    with st.sidebar:
        st.success(f"✅ Logged in as: **{st.session_state.role}**")
        st.info(f"📁 Document access: **{st.session_state.namespace or 'ALL'}**")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.chat_history = []
            st.session_state.qa_chain = None
            st.rerun()

        st.divider()
        st.markdown("### How to use")
        st.markdown("""
        1. Type your question below
        2. The AI will search only **your** documents
        3. You will get an answer based on those documents
        """)

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    user_question = st.chat_input("Ask a question about your documents...")

    if user_question:
        # Show user message
        with st.chat_message("user"):
            st.write(user_question)

        # Add to history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })

        # Get AI answer
        with st.chat_message("assistant"):
            with st.spinner("Searching documents..."):
                try:
                    result = st.session_state.qa_chain.invoke({
                        "question": user_question
                    })

                    answer = result["answer"]
                    source_docs = result.get("source_documents", [])

                    # Show the answer
                    st.write(answer)

                    # Show sources
                    if source_docs:
                        with st.expander("📄 Source documents used"):
                            for i, doc in enumerate(source_docs):
                                st.markdown(f"**Chunk {i+1}:**")
                                st.write(doc.page_content[:300] + "...")
                                st.write(f"*Page: {doc.metadata.get('page', 'N/A')}*")
                                st.divider()

                    # Add answer to history
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer
                    })

                except Exception as e:
                    st.error(f"Error: {str(e)}")
                    st.info("Make sure you have ingested documents for your role first!")