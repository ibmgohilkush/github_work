import streamlit as st
import pandas as pd
import requests

api_key = st.secrets["IBM_API_KEY"]

def extract_text(uploaded_file):
    
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except pd.errors.EmptyDataError:
        return None 

    text = "\n".join(df.astype(str).fillna("").values.flatten())
    return text


def get_auth_token(api_key):
    auth_url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    response = requests.post(auth_url, headers=headers, data=data, verify=False)
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        raise Exception("Failed to get authentication token")

def query_model(messages):
    url = "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29"
    body = {
        "messages": messages,
        "project_id": "ee75eed4-9146-44e2-af95-444d951a4d13",
        "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "decoding_method": "greedy",
        "repetition_penalty": 1,
        "max_tokens": 900
    }
    token = get_auth_token(api_key)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")
    return response.json()['choices'][0]['message']['content']

def main():
    st.title("Analyze Uploaded Excel Feedback")

    uploaded_excel = st.file_uploader("Upload an Excel or .csv file...", type=["xlsx", "csv"])

    if uploaded_excel is not None:
        if uploaded_excel.name.endswith(".csv"):
            df = pd.read_csv(uploaded_excel)
        else:
            df = pd.read_excel(uploaded_excel)

        st.subheader("Preview")
        st.write(df.head())

        analyze_button = st.button("Analyze Feedback")

        if analyze_button:
            uploaded_excel.seek(0)
            text_from_excel = extract_text(uploaded_excel)
            system_prompt = {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "Given the following customer feedback data, please answer in plain English (do not write code):\n"
                        "- Summarize the most common feedback points.\n"
                        "- Only provide a short summary, not code or pseudocode.\n"
                        "- State if the overall sentiment is positive or negative, and briefly reference the evidence supporting that sentiment.\n"
                        "- At the bottom of everything, seperated, if the overall is positive feedback, then just say Positive, else just say Negative.\n\n"
                        f"{text_from_excel}"
                    )}
                ]
            }
            with st.spinner("Analyzing feedback..."):
                ai_response = query_model([system_prompt])
            st.subheader("Analysis Result")
            st.write(ai_response)
    else:
        st.info("Please upload an Excel or .csv file to begin.")

if __name__ == "__main__":  
    main()