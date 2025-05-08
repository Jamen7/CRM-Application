### To obtain industry from person's job tile ###

import pandas as pd
from openai import OpenAI
from local_settings import (
    OPENAI_KEY,
)  # Assumes you have a local_settings.py file in your folder with your OpenAI key

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_KEY)


def llm_chat(message):
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content


# Function to review an article
def get_industry(job_title):
    prompt = f"As an expert, your task is to classify a job title as one of the ten industry categories: technology, healthcare, education, transportation, finance, construction, retail, hospitality, energy and manufacuring. No explanation. are an AI assistant reviewing research articles. Classify this title: {job_title} "

    return llm_chat(prompt)


# Apply the function to each article (assuming "Abstract" is the column name)
# people["industry"] = people["title"].apply(lambda text: get_industry(text) if pd.notna(text) else "No job title provided")

# Load data
people = pd.read_excel("data/crm_test_case_data.xlsx", sheet_name="People")


# Apply the function to each article (assuming "Abstract" is the column name)
people["LLM_Industry"] = people["Title"].apply(
    lambda text: get_industry(text) if pd.notna(text) else "No job title provided"
)

people.to_csv("data/people_industry.csv", index=False)
