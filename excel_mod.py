import streamlit as st
import pandas as pd
import requests

api_key = st.secrets["IBM_API_KEY"]
project_id = st.secrets["PROJECT_ID"]

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
        "project_id": project_id,
        "model_id": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
        "decoding_method": "greedy",
        "repetition_penalty": 1,
        "max_tokens": 2000
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
            #postion our pointer at the starting position 
            uploaded_excel.seek(0)
            text_from_excel = extract_text(uploaded_excel)
            system_prompt = {
                "role": "user",
                "content": [
                    {"type": "text", "text": (
                        "For the following customer feedback data, label each row as either Positive or Negative sentiment. Just do the first 50 rows. Don't give me a code output, just solve it and give me that output."
                        "Return your answer as a two-column table with the original feedback in one column and the sentiment label (Positive/Negative) in the other. "
                        "- Summarize all the feedback into a specific, focused summary that uses evidence from diverse points to understand it.\n"
                        "- Only provide a short summary, not code or pseudocode.\n"
                        "Finally, provide the total count of Positive and Negative labels.\n\n"
                        f"{text_from_excel}"
                    )}
                ]
            }
            with st.spinner("Analyzing feedback..."):
                ai_response = query_model([system_prompt])
            st.subheader("Analysis Result")
            st.write(ai_response)

            # Optional: Try to extract and display counts in the UI if the model outputs them as "Positive: X, Negative: Y"
            import re
            counts = re.findall(r'(Positive|Negative)\s*[:\-]?\s*(\d+)', str(ai_response), re.IGNORECASE)
            if counts:
                st.subheader("Official Sentiment Counts")
                for label, count in counts:
                    st.write(f"{label}: {count}")

    else:
        st.info("Please upload an Excel or .csv file to begin.")

if __name__ == "__main__":  
    main()