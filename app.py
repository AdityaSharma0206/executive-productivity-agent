"""Phase F - Streamlit user-facing Executive Productivity Agent."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from brief_generator import build_brief, load_tasks, render_text
from query_engine import answer

DATA_FILE = BASE_DIR / "data" / "final_tasks.json"

st.set_page_config(
    page_title="Executive Productivity Agent",
    page_icon="📋",
    layout="wide",
)

payload = load_tasks(DATA_FILE)
brief = build_brief(payload)

st.title("Executive Productivity Agent")
st.caption("Phase G — Daily Brief + Natural-Language Query Assistant")

with st.sidebar:
    st.header("Agent")
    st.write("Executive: Arjun Malhotra")
    st.write("Source: Phase D resolved task state")
    st.write("The agent searches the resolved task data and answers in natural language. It does not invent facts.")
    st.divider()
    st.subheader("Try asking")
    examples = [
        "What did I promise Raghav?",
        "When should the presentation be ready?",
        "What's the latest on the Q3 slides?",
        "Who is supposed to handle the Mumbai renewal?",
        "What is going on with the expense report?",
        "Anything I need to follow up on?",
    ]
    for example in examples:
        st.write("• " + example)

tab_brief, tab_chat = st.tabs(["📋 Daily Brief", "💬 Ask the Agent"])

with tab_brief:
    st.subheader("Executive Daily Brief")
    st.info(brief["headline"])

    summary = brief["summary"]
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("My open actions", summary["open_my_actions"])
    c2.metric("Due today", summary["due_today"])
    c3.metric("Overdue", summary["overdue"])
    c4.metric("Waiting on others", summary["waiting_on_others"])
    c5.metric("Ownership unclear", summary["ownership_unclear"])

    st.divider()

    st.subheader("Priorities")
    if brief["priority_actions"]:
        for item in brief["priority_actions"]:
            label = item["reason"].replace("_", " ")
            st.warning(f"**{label}:** {item['title']}")
    else:
        st.success("No immediate priority action identified.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("My Actions")
        if brief["my_actions"]:
            for task in brief["my_actions"]:
                deadline = task["deadline"] or "No deadline"
                flag = " 🔴 OVERDUE" if task["overdue"] else ""
                st.write(f"**{task['title']}**{flag}")
                st.caption(f"Due: {deadline}")
        else:
            st.write("None.")

    with col2:
        st.subheader("Waiting on Others")
        if brief["waiting_on_others"]:
            for task in brief["waiting_on_others"]:
                deadline = task["deadline"] or "No deadline"
                flag = " 🔴 OVERDUE" if task["overdue"] else ""
                st.write(f"**{task['title']}**{flag}")
                st.caption(f"Owner: {task['owner']} · Due: {deadline}")
        else:
            st.write("None.")

    st.subheader("Ownership / Clarity Flags")
    if brief["ownership_unclear"]:
        for task in brief["ownership_unclear"]:
            deadline = task["deadline"] or "No deadline"
            st.error(f"**{task['title']}** — owner unclear · Due: {deadline}")
    else:
        st.write("None.")

    with st.expander("Completed"):
        if brief["completed"]:
            for task in brief["completed"]:
                st.write(f"✓ {task['title']} — {task['completed_on']}")
        else:
            st.write("None.")

with tab_chat:
    st.subheader("Ask the Executive Productivity Agent")
    st.write("Ask naturally about any project, person, document, deadline, status, dependency, commitment, or related work.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask a question about Arjun's tasks...")
    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        response = answer(question, payload)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response, unsafe_allow_html=False)
