import streamlit as st
from modules import page_inspector, goal_maker, timelog_analyzer, tree


st.set_page_config(page_title="AI draugelis seniems programuotojams", layout="wide")
st.sidebar.title("🧭 Nepasiklysk")

tool = st.sidebar.radio("Select Tool", [
    "Taxonomy builder",
    "Are them yankees likely to block?",
    "WHAT and HOW Goal Planner",
    "Time Log Analyzer"
])

if tool == "Taxonomy builder":
    tree.run()
elif tool == "Are them yankees likely to block?":
    page_inspector.run()
elif tool == "WHAT and HOW Goal Planner":
    goal_maker.run()
elif tool == "Time Log Analyzer":
    timelog_analyzer.run()