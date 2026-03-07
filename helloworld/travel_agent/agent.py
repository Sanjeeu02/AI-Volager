from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime
import time

from prompts import MASTER_SYSTEM_PROMPT, AGENT_REASONING_PROMPT
from tools import get_tools

class LangGraphAgentWrapper:
    def __init__(self, api_key):
        self.api_key = api_key
        # Groq free models with tool-use support
        self.primary_model = "llama-3.3-70b-versatile"
        self.fallback_model = "llama-3.1-8b-instant"
        self._current_model = self.primary_model
        self.graph = self._create_graph(self._current_model)

    def _build_system_prompt(self):
        today = datetime.now().strftime("%A, %d %B %Y")   # e.g. Monday, 03 March 2026
        date_context = f"\n\n📅 TODAY'S DATE (use this for all date validation): {today}\n"
        return date_context + MASTER_SYSTEM_PROMPT + "\n\n" + AGENT_REASONING_PROMPT

    def _create_graph(self, model_name):
        llm = ChatGroq(
            model=model_name,
            groq_api_key=self.api_key,
            temperature=0.1,
            max_retries=2,
        )
        tools = get_tools()
        system_prompt = self._build_system_prompt()
        return create_react_agent(llm, tools, prompt=system_prompt)

    def stream_invoke(self, inputs):
        try:
            yield from self._stream_with_model(self.graph, inputs)
        except Exception as e:
            e_str = str(e).lower()
            if ("429" in e_str or "rate_limit" in e_str or "connection error" in e_str or "timeout" in e_str) and self._current_model != self.fallback_model:
                print(f"SWITCHING TO FALLBACK: {self.fallback_model}")
                self._current_model = self.fallback_model
                self.graph = self._create_graph(self._current_model)
                yield f"🔄 Connection issue/Rate limit hit. Switching to fallback model {self.fallback_model}...\n"
                yield from self._stream_with_model(self.graph, inputs)
            else:
                yield f"Error: {e}"

    def _stream_with_model(self, graph, inputs):
        user_input = inputs.get("input")
        chat_history = inputs.get("chat_history", [])
        # Keep only the very last 2 messages (1 Human, 1 AI) to prevent token explosion on free tiers
        truncated_history = chat_history[-2:]
        messages = truncated_history + [HumanMessage(content=user_input)]

        for chunk, metadata in graph.stream(
            {"messages": messages},
            config={"configurable": {"thread_id": "v1"}, "recursion_limit": 10},
            stream_mode="messages"
        ):
            if isinstance(chunk, AIMessage):
                content = chunk.content
                text = self._extract_text(content)
                if text:
                    yield text

    def _extract_text(self, content):
        """Recursively extract clean text from nested content structures, preserving newlines."""
        if isinstance(content, str):
            return content  # Do NOT strip — preserve leading/trailing newlines for markdown
        elif isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    texts.append(str(item["text"]))
                elif isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, list):
                    nested_text = self._extract_text(item)
                    if nested_text:
                        texts.append(nested_text)
            return "".join(texts)  # Join with empty string to preserve markdown structure
        return ""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=1, max=10),
        reraise=True
    )
    def invoke(self, inputs):
        user_input = inputs.get("input")
        chat_history = inputs.get("chat_history", [])
        # Keep only the very last 2 messages (1 Human, 1 AI) to prevent token explosion on free tiers
        truncated_history = chat_history[-2:]
        messages = truncated_history + [HumanMessage(content=user_input)]

        try:
            result_state = self.graph.invoke(
                {"messages": messages},
                config={"configurable": {"thread_id": "v1"}, "recursion_limit": 10}
            )
            last_message = result_state["messages"][-1]
            content = last_message.content
            output_text = "".join([str(b.get("text", b)) if isinstance(b, dict) else str(b) for b in content]) if isinstance(content, list) else str(content)
            return {"output": output_text}
        except Exception as e:
            e_str = str(e).lower()
            if ("429" in e_str or "rate_limit" in e_str or "connection error" in e_str or "timeout" in e_str) and self._current_model != self.fallback_model:
                self._current_model = self.fallback_model
                self.graph = self._create_graph(self._current_model)
                return self.invoke(inputs)
            raise e

def create_travel_agent(api_key: str):
    if not api_key:
        return None
    return LangGraphAgentWrapper(api_key)
