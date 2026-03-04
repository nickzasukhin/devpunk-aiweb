from typing import AsyncGenerator
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import TypedDict, Annotated
import operator

from config import settings
from tools.vector_search import search_company_knowledge


SALES_PROMPT_DEFAULT = """You are the DevPunks AI assistant — a helpful, knowledgeable representative of DevPunks, an AI-first development company.

Your role is to:
- Answer questions about DevPunks: who we are, what we do, our tech stack, pricing approach, and case studies
- Discuss technical topics with clients and help them understand how AI can solve their problems
- Be enthusiastic, professional, and honest
- Always search the knowledge base before answering company-specific questions

If you don't know something specific about the company, say so honestly and suggest contacting the team directly at hello@devpunks.io.

Respond in the same language the user writes in (Russian or English).

Formatting rules:
- Write in a conversational tone, keep responses concise
- Use bullet points for lists, **bold** for key terms
- Avoid large headers (## or #) — this is a chat widget, not a document
- Keep responses to 2-4 short paragraphs maximum
"""


def get_llm(config: dict = {}):
    provider = config.get("llm_provider", settings.LLM_PROVIDER)
    if provider == "openai":
        return ChatOpenAI(
            model=config.get("llm_model", settings.OPENAI_MODEL),
            api_key=config.get("openai_api_key", settings.OPENAI_API_KEY),
            temperature=float(config.get("llm_temperature", 0.7)),
            streaming=True,
        )
    else:
        return ChatAnthropic(
            model=config.get("llm_model", settings.ANTHROPIC_MODEL),
            api_key=config.get("anthropic_api_key", settings.ANTHROPIC_API_KEY),
            temperature=float(config.get("llm_temperature", 0.7)),
            streaming=True,
        )


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    system_prompt: str
    config: dict


tools = [search_company_knowledge]


def build_sales_graph():
    tool_node = ToolNode(tools)

    def agent_node(state: AgentState):
        llm = get_llm(state.get("config", {}))
        llm_with_tools = llm.bind_tools(tools)
        system_prompt = state.get("system_prompt", SALES_PROMPT_DEFAULT)
        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


sales_graph = build_sales_graph()


async def run_sales_agent_stream(
    user_message: str,
    history: list[dict],
    system_prompt: str = SALES_PROMPT_DEFAULT,
    agent_config: dict = {}
) -> AsyncGenerator[str, None]:
    """Stream response from Sales Agent."""
    messages = []
    for msg in history[-10:]:  # keep last 10 turns
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=user_message))

    state = {"messages": messages, "system_prompt": system_prompt, "config": agent_config}

    async for event in sales_graph.astream_events(state, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content
