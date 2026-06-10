from app.rag.schemas import RAGContext


def format_rag_for_sql_prompt(rag: RAGContext) -> str:
    """Format RAG context for injection into SQL generation prompt."""
    if not rag.used or not rag.context_text:
        return ""
    return (
        "\n\n## Contexte métier (RAG)\n"
        "Les informations suivantes proviennent de la documentation interne du projet.\n"
        "Utilise-les pour mieux comprendre les vues disponibles, les règles métier et les exemples SQL.\n\n"
        f"{rag.context_text}\n"
    )


def format_rag_for_answer_prompt(rag: RAGContext) -> str:
    """Format RAG context for injection into professional answer prompt."""
    if not rag.used or not rag.context_text:
        return ""
    return (
        "\n\n## Contexte de référence (documentation interne)\n"
        f"{rag.context_text}\n"
    )


def format_rag_for_insight_prompt(rag: RAGContext) -> str:
    """Format RAG context for injection into entity/page insight prompts."""
    if not rag.used or not rag.context_text:
        return ""
    return (
        "\n\n## Contexte métier et règles de diagnostic\n"
        f"{rag.context_text}\n"
    )
