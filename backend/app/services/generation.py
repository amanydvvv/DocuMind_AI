
import logging
from typing import List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

from app.models import Chunk, Message
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

kwargs = {}
if settings.OMNIROUTE_BASE_URL:
    endpoint = settings.OMNIROUTE_BASE_URL.replace("http://", "").replace("https://", "")
    kwargs["client_options"] = {"api_endpoint": endpoint}

# Initialize the LLM
llm = ChatGoogleGenerativeAI(
    model=settings.GENERATIVE_MODEL,
    google_api_key=settings.GOOGLE_API_KEY or "omniroute_dummy_key",
    temperature=0.2, # Low temperature for more factual responses
    **kwargs
)

RAG_PROMPT_TEMPLATE = """
You are an expert AI assistant tasked with answering questions based ONLY on the provided context and conversation history.

{chat_history_section}

Context information is below.
---------------------
{context}
---------------------

Given the context information, chat history, and no prior knowledge, answer the user's query.
If the answer is not contained in the context, say "I don't have enough information to answer that based on the provided documents."
Do not hallucinate.

User Query: {query}
Answer:
"""

prompt = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["chat_history_section", "context", "query"]
)

async def generate_answer(
    query: str, chunks: List[Chunk], chat_history: Optional[List[Message]] = None
) -> str:
    """
    Generate an answer using the provided chunks as context and prior chat history.
    """
    logger.info("Generating answer based on retrieved context and conversation history...")
    
    # Format context by joining chunk contents
    context_text = "\n\n---\n\n".join(
        [f"Document snippet {i+1}:\n{chunk.content}" for i, chunk in enumerate(chunks)]
    )
    
    # Format chat history if present
    if chat_history:
        history_lines = []
        for msg in chat_history:
            role = "User" if msg.role == "user" else "Assistant"
            history_lines.append(f"{role}: {msg.content}")
        chat_history_section = "Conversation History:\n" + "\n".join(history_lines) + "\n---------------------"
    else:
        chat_history_section = ""
    
    # Build the prompt chain
    chain = prompt | llm
    
    # Execute the LLM
    try:
        response = await chain.ainvoke({
            "chat_history_section": chat_history_section,
            "context": context_text,
            "query": query
        })
        return response.content
    except Exception as e:
        logger.error(f"Error during LLM generation: {e}", exc_info=True)
        raise

