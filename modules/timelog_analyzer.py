import streamlit as st
import pandas as pd
import os
from io import StringIO
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

import streamlit as st

OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

def run():
    st.title("📈 Imma lazy manager - analizuok timelogs už mane")

    st.markdown("Upload CSV time logs for employees. Each file must include these columns:")
    st.code("Name, Week_start, Work_group, Project, Task_name, Hours spent, Comment")

    uploaded_files = st.file_uploader("📂 Upload CSV files", type=["csv"], accept_multiple_files=True)

    if not uploaded_files:
        st.info("⬆️ Kaip tikiesi analizės jei neįkeli duomenų?")
        return

    df_all = pd.DataFrame()
    for file in uploaded_files:
        df = pd.read_csv(file)
        df['Source File'] = file.name
        df_all = pd.concat([df_all, df], ignore_index=True)

    required_columns = {'Name', 'Week_start', 'Work_group', 'Project', 'Task_name', 'Hours spent'}
    if not required_columns.issubset(df_all.columns):
        st.error("❌ Ola Ola netvarkingi failai, susitvarkyk. ")
        return

    # Normalize columns
    df_all['Week_start'] = pd.to_datetime(df_all['Week_start'], errors='coerce')
    df_all['Hours spent'] = pd.to_numeric(df_all['Hours spent'], errors='coerce')

    st.subheader("📊 Raw Combined Data")
    st.dataframe(df_all)

    # Weekly summary
    weekly_summary = df_all.groupby(['Name', 'Week_start'])['Hours spent'].sum().reset_index()
    weekly_summary['Status'] = weekly_summary['Hours spent'].apply(
        lambda x: "✅ OK" if 35 <= x <= 45 else "⚠️ Check: {:.1f}h".format(x)
    )

    st.subheader("🗓️ Weekly Hours Summary")
    st.dataframe(weekly_summary)

    # Aggregates per task/project
    task_summary = df_all.groupby(['Name', 'Work_group', 'Project', 'Task_name'])['Hours spent'].sum().reset_index()
    task_summary = task_summary.sort_values(by='Hours spent', ascending=False)

    st.subheader("📂 Top Logged Tasks/Projects")
    st.dataframe(task_summary)

    # Pattern similarity: same hours on same tasks across weeks
    duplicate_patterns = (
        df_all.groupby(['Name', 'Task_name'])['Hours spent']
        .apply(lambda x: x.nunique() == 1 and len(x) > 1)
        .reset_index()
    )
    suspicious_tasks = duplicate_patterns[duplicate_patterns['Hours spent'] == True]['Task_name'].tolist()

    # AI Summary
    if st.button("🤖 Analyze Patterns with AI"):
        llm = ChatOpenAI(temperature=0.3, model="gpt-4", api_key=OPENAI_API_KEY)
        df_clip = df_all[['Name', 'Week_start', 'Work_group', 'Project', 'Task_name', 'Hours spent']].copy()
        df_clip = df_clip.dropna().astype(str).head(1000)  # limit rows for tokens
        text = df_clip.to_csv(index=False)

        ai_prompt = ChatPromptTemplate.from_template(
            """You are an AI assistant reviewing employee time logs. Each row contains task details and time spent.

Here is a sample of the data:
{csv}

Please summarize:
- Who might be underworking or overworking
- Any repeated or copy-paste patterns
- Any employees overusing the same task or project repeatedly
- Any logs that look suspicious or need manager review
"""
        )

        chain = ai_prompt | llm
        result = chain.invoke({"csv": text})

        st.subheader("🧠 AI Feedback")
        st.text_area("AI Analysis", result.content, height=300)

