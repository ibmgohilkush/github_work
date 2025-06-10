import streamlit as st
import base64
from PIL import Image
import requests
import PyPDF2

api_key = st.secrets["IBM_API_KEY"]

def convert_image_to_base64(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode()
    return base64_image

def extract_text_from_file(uploaded_file):
    if uploaded_file.type == "text/plain":
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.type == "application/pdf":
        reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
        return text
    else:
        return "Unsupported file type."

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
    st.title("Analyze Uploaded Image or Document")

    doc_uploaded = False
    file_uploaded = False

    uploaded_image = st.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
    uploaded_doc = st.file_uploader("Upload a document...", type=["pdf", "txt"])

    if uploaded_image is not None:
        file_uploaded = True
        st.image(Image.open(uploaded_image), caption="Uploaded Image", use_column_width=True)

    if uploaded_doc is not None:
        doc_uploaded = True
        text_preview = extract_text_from_file(uploaded_doc)
        st.subheader("Document Preview")
        st.write(text_preview[:1000] + ("..." if len(text_preview) > 1000 else ""))

    analyze_button = st.button("Analyze")

    if analyze_button:
        if file_uploaded and not doc_uploaded:
            #image analysis
            base64_image = convert_image_to_base64(uploaded_image)
            system_prompt = {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Based on this image, estimate how much money it would cost to repair this. Be clear, and precise, pointing out the specific damages, and then the estimate of each piece that needs to be removed, fixed, replaced, modified, and labor costs. In the estimate, don't use a range like this piece is 500 to 1000, just use one number for each section of the analysis. Try to avoid formatting uses between text and equations, and don't be shy to overestimate."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
            with st.spinner("Analyzing image..."):
                ai_response = query_model([system_prompt])
            st.subheader("Analysis Result")
            st.write(ai_response)
        elif doc_uploaded and not file_uploaded:
            #doc analysis
            text_from_doc = extract_text_from_file(uploaded_doc)
            system_prompt = {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Based on this document, ask 3 thought-provoking questions about its content, themes, or important information you notice."},
                    {"type": "text", "text": text_from_doc}
                ]
            }
            with st.spinner("Analyzing document..."):
                ai_response = query_model([system_prompt])
            st.subheader("Analysis Result")
            st.write(ai_response)
        elif doc_uploaded and file_uploaded:
            st.warning("Please upload only one file at a time (either an image or a document).")
        else:
            st.warning("Please upload a file to analyze.")

if __name__ == "__main__":
    main()
