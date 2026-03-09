import streamlit as st
import os
from dotenv import load_dotenv
from langchain.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
import pandas as pd

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def run():
    st.title("🎯 Kokie planai toliau?")

    st.markdown("Fill in the employee's information, set team and company goals, and generate SMART HOW and WHAT goals personalized to their role and seniority. ")

    with st.form("goal_form"):
        name = st.text_input("👤 Employee Name")
        role = st.text_input("🛠️ Role ")
        how = st.text_input("🛠️ Previous HOW input")
        what = st.text_input("🛠️ Previous WHAT input")

        max_level = st.slider("🛠️ Max Seniority Level in Team", 1, 7, 5)
        emp_level = st.slider("🛠️ This Employee's Seniority Level", 1, max_level, 3)

        team_goals = st.text_area("📌 Team Goals", placeholder="e.g., Improve scraping efficiency, reduce data loss")
        company_goals = st.text_area("🏢 Company Goals", placeholder="e.g., Scale to new markets, ensure compliance")

        submitted = st.form_submit_button("🚀 Generate SMART Goals")

    if submitted:
        if not name or not role or not team_goals or not company_goals:
            st.error("❌ Supildyk iki galo, gi ne daug prašau.")
            return

        seniority_description = describe_seniority(emp_level, max_level)

        llm = ChatOpenAI(temperature=0.3, model="gpt-4", api_key=OPENAI_API_KEY)
        goal_prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant helping a manager define personalized SMART goals. There are WHAT and HOW goals. WHAT goals define what has been done. HOW defines how was it done and focuses more on empathy and collaboration.

Employee Name: {name}  
Role: {role}  
Seniority Level: {level_description} 

Previous or suggested HOW: {how}
Previous or suggested WHAT: {what}

Team Goals: {team_goals}  
Company Goals: {company_goals}  

Generate 3 SMART WHAT (Specific, Measurable, Achievable, Relevant, Time-bound) and 3 HOW goals for this employee."""
        )

        with st.spinner("🧠 Generating SMART goals..."):
            result = (goal_prompt | llm).invoke({
                "name": name,
                "role": role,
                "how" : how,
                "what" : what,
                "level_description": seniority_description,
                "team_goals": team_goals,
                "company_goals": company_goals
            })

        st.subheader(f"✅ SMART Goals for {name}")
        st.text_area("AI-Generated Goals", result.content, height=200)

        df = pd.DataFrame([{
            "Employee": name,
            "Role": role,
            "Seniority": seniority_description,
            "SMART Goals": result.content
        }])
        csv = df.to_csv(index=False)
        st.download_button("📥 Download Goals as CSV", csv, file_name=f"{name}_goals.csv", mime="text/csv")

def describe_seniority(level, max_level):
    levels = {
        1: "Junior",
        2: "Mid-Level",
        3: "Senior",
        4: "Advanced",
        5: "Lead",
        6: "Senior Lead",
        7: "Manager"
    }
    rel_percent = level / max_level
    # Use relative position to label
    if rel_percent <= 0.2:
        return "Junior"
    elif rel_percent <= 0.4:
        return "Mid-Level"
    elif rel_percent <= 0.6:
        return "Senior"
    elif rel_percent <= 0.8:
        return "Advanced"
    else:
        return "Lead/Senior Lead/Manager"
