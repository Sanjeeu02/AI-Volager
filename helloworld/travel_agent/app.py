import streamlit as st
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langchain_groq import ChatGroq
from agent import create_travel_agent
from prompts import VLOG_SCRIPT_PROMPT

load_dotenv()

CHAT_HISTORY_FILE = "chat_history.json"

# ── Persist helpers ───────────────────────────────────────────────────────────
def save_chat_history(messages):
    data = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            data.append({"role": "ai", "content": msg.content})
        elif isinstance(msg, HumanMessage):
            data.append({"role": "human", "content": msg.content})
    with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat_history():
    if not os.path.exists(CHAT_HISTORY_FILE):
        return None
    try:
        with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = []
        for item in data:
            if item["role"] == "ai":
                messages.append(AIMessage(content=item["content"]))
            else:
                messages.append(HumanMessage(content=item["content"]))
        return messages if messages else None
    except Exception:
        return None

def clear_chat_history():
    if os.path.exists(CHAT_HISTORY_FILE):
        os.remove(CHAT_HISTORY_FILE)

def extract_trip_title(content: str) -> str:
    """Try to extract 'Source → Destination' from an AI message."""
    for line in content.splitlines():
        if "➡️" in line or "→" in line:
            clean = line.replace("#", "").replace("*", "").strip()
            if len(clean) < 80:
                return clean
    return "Trip Plan"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Voyager | Premium Travel Planning",
    page_icon="✈️",
    layout="wide"
)

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='text-align:center;padding:1rem'>"
        "<h2 style='color:#3B82F6'>🚀 Voyager AI</h2></div>",
        unsafe_allow_html=True,
    )

    st.header("🔑 API Key")
    env_key = os.getenv("GROQ_API_KEY")
    api_key_input = st.text_input(
        "Groq API Key (Free)",
        value=env_key if env_key else "",
        type="password",
        autocomplete="current-password",
        help="Get your FREE key at https://console.groq.com",
    )
    api_key = api_key_input if api_key_input else None

    st.markdown("---")
    st.header("🗂️ Chat History")
    total_msgs = len(load_chat_history() or [])
    if total_msgs > 0:
        st.success(f"📜 {total_msgs} messages saved")
        if st.button("🗑️ Clear All History", use_container_width=True):
            clear_chat_history()
            st.session_state.pop("messages", None)
            st.session_state.pop("reuse_query", None)
            st.rerun()
    else:
        st.info("No history yet.")

    st.markdown("---")
    st.caption("Powered by Groq · Llama 3.3 70B")

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-section">
    <div class="hero-title">✈️ AI Voyager</div>
    <div class="hero-subtitle">YOUR AUTONOMOUS GATEWAY TO THE WORLD</div>
</div>
""", unsafe_allow_html=True)

if not api_key:
    st.warning("⚠️ Please enter your **Groq API Key** in the sidebar to start planning!")
    st.info("""
💡 **Get your FREE Groq API Key (takes 2 minutes):**
1. Visit [console.groq.com](https://console.groq.com)
2. Sign up with Google or email — **no credit card needed**
3. Go to **API Keys** → click **Create API Key**
4. Paste it in the sidebar 👈

Groq is 100% free and uses **Llama 3.3 70B** — a powerful AI that never expires!
""")
    st.stop()

# ── Agent init ────────────────────────────────────────────────────────────────
if "agent_executor" not in st.session_state or st.session_state.get("last_key") != api_key:
    st.session_state.agent_executor = create_travel_agent(api_key)
    st.session_state.last_key = api_key

WELCOME_MSG = AIMessage(content="""👋 **Welcome back to Voyager AI!**

I'm your personal AI travel concierge. I'll plan your perfect trip with transport, hotels, attractions and a full budget breakdown — all tailored to **your budget**!

**Just say something like:**
> *"Plan a trip from Mumbai to Goa for 2 people on March 10 with ₹5000 budget"*

Let's go! 🌍✈️""")

if "messages" not in st.session_state:
    saved = load_chat_history()
    st.session_state.messages = saved if saved else [WELCOME_MSG]

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_chat, tab_history, tab_itinerary, tab_bookings, tab_vlog = st.tabs([
    "💬 Chat",
    "🗂️ History",
    "🗺️ My Itinerary",
    "🎫 Bookings",
    "🎬 Vlog Script"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — CHAT
# ══════════════════════════════════════════════════════════════════
with tab_chat:
    # Pre-fill input from history reuse
    default_input = st.session_state.pop("reuse_query", "")

    num_human = sum(1 for m in st.session_state.messages if isinstance(m, HumanMessage))
    if num_human > 0:
        st.caption(f"🗂️ Session active — {num_human} message(s) in history")

    for msg in st.session_state.messages:
        if isinstance(msg, AIMessage):
            with st.chat_message("ai", avatar="🤖"):
                st.markdown(msg.content)
        elif isinstance(msg, HumanMessage):
            with st.chat_message("human", avatar="👤"):
                st.markdown(msg.content)

    prompt = st.chat_input(
        placeholder=default_input if default_input else "Where should we go? ✈️",
        key="main_chat_input"
    )
    # If reuse was triggered, auto-submit it
    if default_input and not prompt:
        prompt = default_input

    if prompt:
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("human", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("ai", avatar="🤖"):
            if st.session_state.agent_executor:
                chat_history = st.session_state.messages[:-1]
                with st.spinner("✈️ Finding the best options for your budget..."):
                    try:
                        response_stream = st.session_state.agent_executor.stream_invoke(
                            {"input": prompt, "chat_history": chat_history}
                        )
                        full_response = ""
                        for chunk in response_stream:
                            if chunk:
                                full_response += chunk

                        if full_response:
                            st.markdown(full_response)
                            st.session_state.messages.append(AIMessage(content=full_response))
                            save_chat_history(st.session_state.messages)
                            st.rerun()

                    except Exception as e:
                        if "429" in str(e) or "rate_limit" in str(e).lower():
                            st.error("🚀 Too many requests. Please wait a moment and try again.")
                        else:
                            st.error(f"❌ Error: {e}")

# ══════════════════════════════════════════════════════════════════
# TAB 2 — HISTORY
# ══════════════════════════════════════════════════════════════════
with tab_history:
    st.header("🗂️ Chat History")
    st.caption("Browse your past conversations. Click **♻️ Reuse** to start a similar trip!")

    messages = st.session_state.messages
    if len(messages) <= 1:
        st.info("💬 No chat history yet. Start a conversation in the Chat tab!")
    else:
        # Build pairs: (human_msg, ai_response)
        pairs = []
        i = 0
        while i < len(messages):
            if isinstance(messages[i], HumanMessage):
                human_msg = messages[i]
                ai_msg = messages[i + 1] if i + 1 < len(messages) and isinstance(messages[i + 1], AIMessage) else None
                pairs.append((i, human_msg, ai_msg))
                i += 2
            else:
                i += 1

        # Skip the welcome message pair
        user_pairs = [(idx, h, a) for idx, h, a in pairs if not h.content.startswith("👋")]

        if not user_pairs:
            st.info("💬 No trips planned yet. Head to the Chat tab and ask me to plan a trip!")
        else:
            st.success(f"📜 **{len(user_pairs)} conversation(s) found**")
            st.divider()

            for count, (idx, human_msg, ai_msg) in enumerate(reversed(user_pairs), 1):
                # Extract trip title
                title = extract_trip_title(ai_msg.content) if ai_msg else f"Conversation {count}"
                label = f"🧳 Trip {count}: {title[:60]}..." if len(title) > 60 else f"🧳 Trip {count}: {title}"

                with st.expander(label, expanded=(count == 1)):
                    # Show human question
                    st.markdown("**🗣️ Your Message:**")
                    with st.chat_message("human", avatar="👤"):
                        st.markdown(human_msg.content)

                    if ai_msg:
                        st.markdown("**🤖 Voyager AI Response:**")
                        with st.chat_message("ai", avatar="🤖"):
                            st.markdown(ai_msg.content)

                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"♻️ Reuse This Trip", key=f"reuse_{idx}", use_container_width=True):
                            st.session_state.reuse_query = human_msg.content
                            st.rerun()
                    with col2:
                        if st.button(f"📋 Copy Query", key=f"copy_{idx}", use_container_width=True):
                            st.code(human_msg.content)
                    with col3:
                        if st.button(f"🗑️ Delete", key=f"del_{idx}", use_container_width=True):
                            # Remove the human_msg and ai_msg from session state
                            if ai_msg:
                                st.session_state.messages = [m for m in st.session_state.messages if m != human_msg and m != ai_msg]
                            else:
                                st.session_state.messages = [m for m in st.session_state.messages if m != human_msg]
                            save_chat_history(st.session_state.messages)
                            st.rerun()

# ══════════════════════════════════════════════════════════════════
# TAB 3 — ITINERARY
# ══════════════════════════════════════════════════════════════════
with tab_itinerary:
    st.header("📍 Your Latest Trip Plan")
    plan_msg = None
    for msg in reversed(st.session_state.messages):
        if isinstance(msg, AIMessage) and ("Trip Plan" in msg.content or "➡️" in msg.content):
            plan_msg = msg
            break
    if plan_msg:
        st.markdown(plan_msg.content)
    elif len(st.session_state.messages) > 1:
        last = st.session_state.messages[-1]
        if isinstance(last, AIMessage):
            st.markdown(last.content)
    else:
        st.info("💬 Start a conversation to see your trip plan here!")

# ══════════════════════════════════════════════════════════════════
# TAB 4 — BOOKINGS
# ══════════════════════════════════════════════════════════════════
with tab_bookings:
    st.header("🎫 My Bookings")
    booking_msgs = [
        msg for msg in st.session_state.messages
        if isinstance(msg, AIMessage) and "Booking" in msg.content and "Confirmed" in msg.content
    ]
    if booking_msgs:
        for bm in booking_msgs:
            st.markdown(bm.content)
            st.divider()
    else:
        st.info("No bookings yet. Plan a trip in the Chat tab and confirm a booking!")
        st.caption("Your booking confirmations will appear here automatically once confirmed.")

# ══════════════════════════════════════════════════════════════════
# TAB 5 — VLOG SCRIPT GENERATOR
# ══════════════════════════════════════════════════════════════════
with tab_vlog:
    st.header("🎬 YouTube Travel Vlog Script Generator")
    st.caption("Generate a professional, natural-sounding vlog script for any destination — in seconds!")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        vlog_topic = st.text_input(
            "📍 Destination / Trip Title",
            placeholder="e.g. 3 Days Trip to Manali",
            key="vlog_topic"
        )
        vlog_tone = st.selectbox(
            "🎤 Tone",
            ["Exciting & Energetic", "Friendly & Casual", "Informative & Professional", "Humorous & Fun", "Inspiring & Motivational"],
            key="vlog_tone"
        )
        vlog_days = st.number_input(
            "📅 Trip Duration (days)",
            min_value=1, max_value=30, value=3, step=1,
            key="vlog_days"
        )

    with col2:
        vlog_audience = st.selectbox(
            "👥 Target Audience",
            ["Young travelers & College students", "Budget backpackers", "Families with kids", "Solo travelers", "Couples", "Luxury travelers"],
            key="vlog_audience"
        )
        vlog_length = st.selectbox(
            "⏱️ Video Length",
            ["3 minutes", "5 minutes", "8 minutes", "10 minutes", "15 minutes"],
            index=1,
            key="vlog_length"
        )

    st.divider()

    generate_btn = st.button("🎬 Generate Vlog Script", type="primary", use_container_width=True, key="gen_vlog")

    if generate_btn:
        if not vlog_topic.strip():
            st.error("⚠️ Please enter a destination or trip title!")
        else:
            # Only confirmed active Groq production models (March 2026)
            FALLBACK_MODELS = [
                ("llama-3.3-70b-versatile", "Llama 3.3 70B"),
                ("llama-3.1-8b-instant",    "Llama 3.1 8B"),
            ]

            filled_prompt = VLOG_SCRIPT_PROMPT.format(
                topic=vlog_topic,
                tone=vlog_tone,
                audience=vlog_audience,
                video_length=vlog_length,
                duration_days=vlog_days,
            )

            script = None
            last_error = None

            progress = st.empty()

            for model_id, model_name in FALLBACK_MODELS:
                try:
                    progress.info(f"🤖 Trying **{model_name}**... generating your script!")
                    llm = ChatGroq(
                        model=model_id,
                        groq_api_key=api_key,
                        temperature=0.75,
                        max_retries=1,
                    )
                    response = llm.invoke(filled_prompt)
                    script = response.content
                    progress.success(f"✅ Script generated using **{model_name}**!")
                    break  # success — stop trying

                except Exception as e:
                    last_error = str(e)
                    # Continue to next model for: rate limits, connection errors, decommissioned, overloaded
                    should_skip = (
                        "429" in last_error
                        or "rate_limit" in last_error.lower()
                        or "overloaded" in last_error.lower()
                        or "model_decommissioned" in last_error.lower()
                        or "decommissioned" in last_error.lower()
                        or "no longer supported" in last_error.lower()
                        or "connection error" in last_error.lower()
                        or "timeout" in last_error.lower()
                    )
                    if should_skip:
                        progress.warning(f"⚠️ **{model_name}** busy/unavailable — switching to next model...")
                        import time
                        time.sleep(1)
                        continue  # try next model
                    else:
                        progress.error(f"❌ Error: {last_error}")
                        break

            if script:
                st.divider()
                st.markdown(script)
                st.divider()
                st.download_button(
                    label="⬇️ Download Script as .txt",
                    data=script,
                    file_name=f"vlog_script_{vlog_topic.replace(' ', '_')}.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
            elif not script and last_error:
                st.error("""
⚠️ **All models are temporarily rate-limited.**

This happens when too many requests are sent quickly on the free Groq plan.

**What to do:**
- ⏳ Wait **1–2 minutes** and try again
- 🔁 Groq free limits reset every minute
- 💡 Or try a shorter video length to reduce token usage
""")

