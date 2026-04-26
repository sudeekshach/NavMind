import streamlit as st
import subprocess
import requests
import time

OLLAMA_URL = "http://172.18.208.1:11434/api/generate"
MODEL = "llama3.2:1b"

ROOMS = [
    "living room", "dining room", "kitchen",
    "study", "bedroom", "guest room"
]

def ask_llm(prompt):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        }, timeout=30)
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"LLM error: {e}"

def parse_room(user_input):
    user_input_lower = user_input.lower()
    # Require cleaning intent
    cleaning_words = ["clean", "vacuum", "sweep", "tidy", "mop", "go to", "navigate", "cover"]
    has_intent = any(word in user_input_lower for word in cleaning_words)
    if not has_intent:
        return None
    for room in ROOMS:
        if room in user_input_lower:
            return room
    return None

def send_command(room_name):
    cmd = f'source /opt/ros/humble/setup.bash && ros2 topic pub /navmind/command std_msgs/msg/String "{{data: \'{room_name}\'}}" --once'
    subprocess.run(cmd, shell=True, executable='/bin/bash')

def get_latest_commentary():
    try:
        result = subprocess.run(
            'source /opt/ros/humble/setup.bash && timeout 2 ros2 topic echo /navmind/commentary --once 2>/dev/null',
            shell=True, executable='/bin/bash',
            capture_output=True, text=True, timeout=3
        )
        if 'data:' in result.stdout:
            return result.stdout.split('data:')[1].strip().strip("'\"")
    except:
        pass
    return None

def get_status():
    try:
        result = subprocess.run(
            'source /opt/ros/humble/setup.bash && timeout 2 ros2 topic echo /navmind/status --once 2>/dev/null',
            shell=True, executable='/bin/bash',
            capture_output=True, text=True, timeout=3
        )
        if 'data:' in result.stdout:
            return result.stdout.split('data:')[1].strip().strip("'\"")
    except:
        pass
    return "idle"

# UI
st.set_page_config(page_title="NavMind", page_icon="🤖", layout="wide")
st.title("🤖 NavMind — AI Home Robot")
st.caption("Natural language navigation + autonomous room coverage")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar
with st.sidebar:
    st.header("🏠 Rooms")
    for room in ROOMS:
        st.write(f"📍 {room.title()}")
    st.divider()
    status = get_status()
    st.header("📊 Status")
    if "navigating" in status:
        st.warning(f"🧭 Navigating to {status.split(':')[-1]}")
    elif "covering" in status:
        st.success(f"🧹 Cleaning {status.split(':')[-1]}")
    elif "complete" in status:
        st.success(f"✅ Completed {status.split(':')[-1]}")
    else:
        st.info("⚪ Robot is ready")

# Display messages
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])
    elif msg["role"] == "robot":
        st.chat_message("assistant", avatar="🤖").write(msg["content"])
    elif msg["role"] == "system":
        st.info(msg["content"])

# Auto-refresh commentary
if any("covering" in get_status() or "navigating" in get_status() for _ in [1]):
    commentary = get_latest_commentary()
    if commentary and (not st.session_state.messages or 
                       st.session_state.messages[-1].get("content") != f"🤖 {commentary}"):
        st.session_state.messages.append({
            "role": "robot",
            "content": f"🤖 {commentary}"
        })
        st.rerun()

# Chat input
if prompt := st.chat_input("Tell NavMind what to do... (e.g. 'Clean the kitchen')"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    room_name = parse_room(prompt)

    if room_name:
        st.session_state.messages.append({
            "role": "system",
            "content": f"🧹 Sending command: clean the {room_name}..."
        })
        send_command(room_name)
        time.sleep(2)
        commentary = get_latest_commentary()
        if commentary:
            st.session_state.messages.append({
                "role": "robot",
                "content": f"🤖 {commentary}"
            })
        else:
            st.session_state.messages.append({
                "role": "robot",
                "content": f"🤖 On my way to clean the {room_name}!"
            })
    else:
        response = ask_llm(f"""You are NavMind, a friendly home robot assistant.
User said: "{prompt}"
You can clean these rooms: {', '.join(ROOMS)}.
Respond naturally and helpfully. If they want cleaning, ask which room.""")
        st.session_state.messages.append({
            "role": "robot",
            "content": f"🤖 {response}"
        })

    st.rerun()
