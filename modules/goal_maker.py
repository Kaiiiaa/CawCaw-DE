import os
from dotenv import load_dotenv
import pandas as pd
import streamlit as st

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]


def run():
    st.title("🎯 Kokie planai toliau?")

    st.markdown(
        "Fill in the employee's information, set team and company goals, and generate SMART HOW and WHAT goals personalized to their role and seniority."
    )

    with st.form("goal_form"):
        name = st.text_input("👤 Employee Name")
        role = st.text_input("🛠️ Role ")
        how = st.text_input("🛠️ Previous HOW input")
        what = st.text_input("🛠️ Previous WHAT input")

        max_level = st.slider("🛠️ Max Seniority Level in Team", 1, 7, 5)
        emp_level = st.slider("🛠️ This Employee's Seniority Level", 1, max_level, 3)

        objectives = st.text_area(
            "📌 Last 6 months objectives",
            placeholder="e.g., Scraped x pages, overall crawler performance was 98%"
        )
        improvements = st.text_area(
            "🏢 Employee improvement areas",
            placeholder="e.g., Better communication, etc."
        )
        company_goals = st.text_area(
            "🏢 Company Goals",
            placeholder="e.g., Scale to new markets, ensure compliance"
        )

        submitted = st.form_submit_button("🚀 Generate SMART Goals")

    if submitted:
        if not name or not role or not objectives or not improvements or not company_goals:
            st.error("❌ Supildyk iki galo, gi ne daug prašau.")
            return

        seniority_description = describe_seniority(emp_level, max_level)

        llm = ChatOpenAI(
            temperature=0.3,
            model="gpt-4",
            api_key=OPENAI_API_KEY
        )

        goal_prompt = ChatPromptTemplate.from_template(
            """
You are an AI assistant helping a manager define personalized SMART goals.

There are:
- WHAT goals: what has to be achieved
- HOW goals: how the work should be done, with focus on empathy, collaboration, ownership, and communication

Employee Name: {name}
Role: {role}
Seniority Level: {level_description}

Previous or suggested HOW: {how}
Previous or suggested WHAT: {what}

Last 6 months performed objectives: {objectives}
Improvements: {improvements}
Company Goals: {company_goals}

Return the response in exactly this format:

SMART Goals:
[Write 3 SMART WHAT goals and 3 HOW goals here]

Performance Review:
[Write a short performance review here, max 5 sentences, simple language]
"""
        )

        with st.spinner("🧠 Generating SMART goals..."):
            result = (goal_prompt | llm).invoke({
                "name": name,
                "role": role,
                "how": how,
                "what": what,
                "level_description": seniority_description,
                "objectives": objectives,
                "improvements": improvements,
                "company_goals": company_goals
            })

        full_text = result.content

        smart_goals = ""
        performance_review = ""

        if "Performance Review:" in full_text:
            parts = full_text.split("Performance Review:", 1)
            smart_goals = parts[0].replace("SMART Goals:", "").strip()
            performance_review = parts[1].strip()
        else:
            smart_goals = full_text.strip()
            performance_review = ""

        st.subheader(f"✅ SMART Goals for {name}")
        st.text_area("SMART Goals", smart_goals, height=250)

        st.subheader("📝 Performance Review")
        st.text_area("Performance Review", performance_review, height=150)

        df = pd.DataFrame([{
            "Employee": name,
            "Role": role,
            "Seniority": seniority_description,
            "SMART Goals": smart_goals,
            "Performance Review": performance_review
        }])

        csv = df.to_csv(index=False)

        st.download_button(
            "📥 Download Goals as CSV",
            csv,
            file_name=f"{name}_goals.csv",
            mime="text/csv"
        )


def describe_seniority(level, max_level):
    rel_percent = level / max_level

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
