"""LangChain RAG answer pipeline with an optional Groq chat model."""

import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from rag.retrieval import search_events

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Answer questions about cricket logs using only the supplied event records. "
            "Do not infer unsupported facts. Say when the evidence is insufficient. "
            "Note data quality flags when relevant.",
        ),
        ("human", "Question: {question}\n\nRetrieved records:\n{context}"),
    ]
)


def _format_context(matches: list[dict]) -> str:
    return "\n\n".join(
        f"[{match['event_id']}] Match={match['match_id']}; team={match['team']}; "
        f"player={match['player']}; event={match['event_type']}; runs={match['runs']}; "
        f"over={match['over']}; status={match['status']}; timestamp={match['timestamp']}; "
        f"commentary={match['commentary']}; flags={match['quality_flags']}"
        for match in matches
    )


def answer_question(question: str, top_k: int = 5) -> dict:
    """Retrieve LangChain documents and optionally generate a grounded answer."""
    matches = search_events(question, top_k=top_k)
    if not matches:
        return {
            "answer": "No indexed cricket events were found.",
            "sources": [],
            "retrieval": {"strategy": "semantic_similarity", "top_k": top_k},
        }

    context = _format_context(matches)
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        answer = (
            "I retrieved the closest matching events. Add GROQ_API_KEY to .env to enable "
            "generated natural-language answers. For now, use the returned sources as evidence.\n\n"
            + context
        )
    else:
        chain = RAG_PROMPT | ChatGroq(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            temperature=0,
        ) | StrOutputParser()
        answer = chain.invoke({"question": question, "context": context})

    return {
        "answer": answer,
        "sources": matches,
        "retrieval": {"strategy": "semantic_similarity", "top_k": top_k},
    }
