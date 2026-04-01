# app.py - Main chatbot application

import os
import streamlit as st
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.messages import HumanMessage, SystemMessage
from auth import login, get_allowed_namespace, add_user, delete_user, get_all_users

# Load API keys
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# All available company namespaces
ALL_NAMESPACES = ["walmart", "tesla", "amazon", "google", "microsoft"]


def get_answer(question: str, namespace: str, chat_history: list):
    """
    Searches Pinecone for relevant chunks and sends to GPT to get an answer.
    Admin searches all namespaces, other users search only their namespace.
    """
    embeddings = OpenAIEmbeddings(api_key=OPENAI_API_KEY)

    # If admin, search all namespaces and combine results
    if namespace is None:
        all_docs = []
        for ns in ALL_NAMESPACES:
            try:
                vectorstore = PineconeVectorStore(
                    index_name=INDEX_NAME,
                    embedding=embeddings,
                    namespace=ns,
                    pinecone_api_key=PINECONE_API_KEY
                )
                docs = vectorstore.similarity_search(question, k=2)
                all_docs.extend(docs)
            except Exception:
                continue
        docs = all_docs
    else:
        # Regular user - search only their namespace
        vectorstore = PineconeVectorStore(
            index_name=INDEX_NAME,
            embedding=embeddings,
            namespace=namespace,
            pinecone_api_key=PINECONE_API_KEY
        )
        docs = vectorstore.similarity_search(question, k=4)

    # Build context from retrieved chunks
    context = "\n\n".join([doc.page_content for doc in docs])

    # Build conversation history
    history_text = ""
    for msg in chat_history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    # Set up the AI model
    llm = ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model="gpt-3.5-turbo",
        temperature=0
    )

    # Build the prompt
    messages = [
        SystemMessage(content=f"""You are a helpful enterprise assistant that answers 
        questions based ONLY on the provided document context.
        Each document chunk has metadata showing which company it belongs to in source_file.
        When answering, always identify which company each piece of information comes from
        using the source_file metadata. For example say "Walmart's revenue was..." 
        instead of "the company's revenue was...".
        If the answer is not in the context, say 
        "I don't have that information in the documents I have access to."
        Do not make up answers or use outside knowledge.
        
        Document Context:
        {context}
        
        Previous conversation:
        {history_text}
        """),
        HumanMessage(content=question)
    ]

    response = llm.invoke(messages)
    return response.content, docs


# ─── Page Config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="RAG RBAC Chatbot",
    page_icon="🤖",
    layout="wide"
)

# ─── Session State Setup ──────────────────────────────────────────────────────

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = None
if "namespace" not in st.session_state:
    st.session_state.namespace = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# ─── Login Screen ─────────────────────────────────────────────────────────────

if not st.session_state.logged_in:

    st.title("🤖 RAG Chatbot with Role-Based Access Control")
    st.markdown("---")
    st.subheader("Please log in to continue")

    col1, col2 = st.columns([1, 2])

    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if not username or not password:
                st.warning("Please enter both username and password.")
            else:
                role = login(username, password)
                if role:
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.namespace = get_allowed_namespace(role)
                    st.session_state.chat_history = []
                    st.success(f"Welcome! Logged in as: {role}")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please try again.")

    with col2:
        st.info("""
        **Enterprise Document Assistant**

        This is a secure Role-Based Access Control (RBAC) RAG Chatbot.
        
        Each user can only access documents assigned to their role.
        Unauthorized document access is automatically restricted.
        
        Please contact your administrator for login credentials.
        """)

        st.markdown("---")
        st.markdown("**How it works:**")
        st.markdown("""
        - 🔐 Login with your credentials
        - 📁 Access only your authorized documents  
        - 💬 Ask questions in natural language
        - 🤖 Get AI-powered answers from your documents
        """)

# ─── Chat Screen ──────────────────────────────────────────────────────────────

else:
    # Sidebar
    with st.sidebar:
        st.title("🤖 RAG RBAC Chatbot")
        st.markdown("---")
        st.success(f"✅ Logged in as: **{st.session_state.role}**")
        st.info(f"📁 Document access: **{st.session_state.namespace or 'ALL DOCUMENTS'}**")
        st.markdown("---")

        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.namespace = None
            st.session_state.chat_history = []
            st.rerun()

        st.markdown("---")
        st.markdown("### 💡 How to use")
        st.markdown("""
        1. Type your question below
        2. AI searches only **your** authorized documents
        3. Get accurate answers with source references
        4. Ask follow-up questions naturally
        """)

        st.markdown("---")
        st.markdown("### ⚠️ Access Control")
        st.markdown("""
        You can only query documents assigned to your role.
        Attempts to access unauthorized documents will be blocked.
        """)

        if st.session_state.chat_history:
            msg_count = len(st.session_state.chat_history)
            st.markdown("---")
            st.markdown(f"💬 **{msg_count} messages** in this session")
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        # ─── Admin Panel ──────────────────────────────────────────────────────
        if st.session_state.role == "admin":
            st.markdown("---")
            st.markdown("### 🔧 Admin Panel")

            with st.expander("➕ Add New User"):
                new_username = st.text_input("Username", key="new_username")
                new_password = st.text_input("Password", key="new_password")
                new_role = st.text_input(
                    "Role (e.g. walmart, tesla)",
                    key="new_role"
                )
                if st.button("Add User", key="add_user_btn"):
                    if new_username and new_password and new_role:
                        success, msg = add_user(
                            new_username,
                            new_password,
                            new_role
                        )
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please fill in all fields.")

            with st.expander("🗑️ Delete User"):
                all_users = get_all_users()
                deletable_users = [
                    u for u in all_users.keys() if u != "admin"
                ]
                if deletable_users:
                    user_to_delete = st.selectbox(
                        "Select user to delete",
                        options=deletable_users,
                        key="delete_user_select"
                    )
                    if st.button("Delete User", key="delete_user_btn"):
                        success, msg = delete_user(user_to_delete)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                else:
                    st.info("No users to delete.")

            with st.expander("👥 View All Users"):
                all_users = get_all_users()
                for uname, udata in all_users.items():
                    st.markdown(f"**{uname}** → role: `{udata['role']}`")

    # ─── Main Chat Area ───────────────────────────────────────────────────────

    st.title("💬 Document Assistant")
    st.markdown(
        f"Logged in as **{st.session_state.role}** — "
        f"accessing **{st.session_state.namespace or 'ALL'}** documents"
    )
    st.markdown("---")

    # Show example questions if no chat history yet
    if not st.session_state.chat_history:
        st.markdown("### 👋 Welcome! Ask me anything about your documents.")
        st.markdown("Some example questions:")

        if st.session_state.namespace == "walmart":
            st.markdown("""
            - *What was Walmart's total revenue in 2024?*
            - *What are Walmart's main business segments?*
            - *How many employees does Walmart have?*
            """)
        elif st.session_state.namespace == "tesla":
            st.markdown("""
            - *What was Tesla's net income in 2024?*
            - *How many vehicles did Tesla deliver in 2024?*
            - *What are Tesla's main revenue streams?*
            """)
        elif st.session_state.namespace == "amazon":
            st.markdown("""
            - *What was Amazon's total revenue in 2024?*
            - *How did AWS perform in 2024?*
            - *What are Amazon's main business segments?*
            """)
        elif st.session_state.namespace == "google":
            st.markdown("""
            - *What was Google's total revenue in 2024?*
            - *How did Google Cloud perform in 2024?*
            - *What are Alphabet's main revenue streams?*
            """)
        elif st.session_state.namespace == "microsoft":
            st.markdown("""
            - *What was Microsoft's total revenue in 2024?*
            - *How did Azure perform in 2024?*
            - *What are Microsoft's main business segments?*
            """)
        else:
            st.markdown("""
            - *What was the total revenue for each company?*
            - *Compare Walmart and Tesla's performance.*
            - *What are the key highlights from 2024?*
            """)

    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    user_question = st.chat_input("Ask a question about your documents...")

    if user_question:
        with st.chat_message("user"):
            st.write(user_question)

        st.session_state.chat_history.append({
            "role": "user",
            "content": user_question
        })

        with st.chat_message("assistant"):
            with st.spinner("🔍 Searching your documents..."):
                try:
                    answer, source_docs = get_answer(
                        user_question,
                        st.session_state.namespace,
                        st.session_state.chat_history
                    )

                    st.write(answer)

                    if source_docs:
                        with st.expander("📄 View source documents used"):
                            for i, doc in enumerate(source_docs):
                                st.markdown(f"**Source {i+1}:**")
                                st.write(doc.page_content[:300] + "...")
                                st.caption(
                                    f"Page: {doc.metadata.get('page', 'N/A')} | "
                                    f"File: {doc.metadata.get('source_file', 'N/A')}"
                                )
                                st.divider()

                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": answer
                    })

                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.info(
                        "Please make sure documents have been ingested for your role."
                    )


