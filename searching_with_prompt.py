import streamlit as st
import base64
from PIL import Image
import requests
from bs4 import BeautifulSoup


api_key = st.secrets["IBM_API_KEY"]
project_id = st.secrets["PROJECT_ID"]
serpapi_key = st.secrets["SERPAPI_KEY"]

def convert_image_to_base64(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode()
    return base64_image

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

def search_web(query):
    search_url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": serpapi_key,
        #we don't want to use too many tokens or resources 
        "num": 2  
    }

    response = requests.get(search_url, params=params)
    results = response.json()

    snippets = ""
    for item in results.get("organic_results", []):
        title = item.get("title", "")
        link = item.get("link", "")

        try:
            page = requests.get(link, timeout=5)
            soup = BeautifulSoup(page.text, "html.parser")
            paragraphs = soup.find_all("p")
            page_text = " ".join(p.get_text() for p in paragraphs[:5]) 
            cleaned_text = page_text.replace("\n", " ").strip()

            snippets += f"🔹 **{title}**\nFrom {link}:\n{cleaned_text}\n\n"

        except Exception as e:
            snippets += f"🔹 **{title}**\n{link}\n⚠️ Could not fetch page content: {str(e)}\n\n"

    return snippets.strip()

def main():
    st.title("Chat with Images and Internet Search")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = False

    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image, caption='Uploaded Image', use_column_width=True)
            base64_image = convert_image_to_base64(uploaded_file)
            if st.session_state.uploaded_file == False:
                st.session_state.messages.append({
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]
                })
                st.session_state.uploaded_file = True

    for msg in st.session_state.messages[1:]:
        if msg['role'] == "user":
            with st.chat_message("user"):
                if msg['content'][0]['type'] == "text":
                    st.write(msg['content'][0]['text'])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("Type your message here...")

    if user_input:
        message = {"role": "user", "content": [{"type": "text", "text": user_input}]}
        st.session_state.messages.append(message)
        st.chat_message(message['role']).write(user_input)

        model_messages = []
        latest_image_url = None
        for msg in st.session_state.messages:
            if msg["role"] == "user" and isinstance(msg["content"], list):
                content = []
                for item in msg["content"]:
                    if item["type"] == "text":
                        content.append(item)
                    elif item["type"] == "image_url":
                        latest_image_url = item
                if latest_image_url:
                    content.append(latest_image_url)
                model_messages.append({"role": msg["role"], "content": content})
            else:
                model_messages.append({
                    "role": msg["role"],
                    "content": [{"type": "text", "text": msg["content"]}] if isinstance(msg["content"], str) else msg["content"]
                })

        # 🔍 Inject Web Search (if relevant)
        web_keywords = ["search", "news", "find", "lookup", "documentation"]
        if any(keyword in user_input.lower() for keyword in web_keywords):
            try:
                snippets = search_web(user_input)
                if snippets:
                    model_messages[-1]["content"].insert(0, {
                        "type": "text",
                        "text": f"Here are the top web search results relevant to your query:\n\n{snippets}"
                    })
            except Exception as e:
                st.warning(f"Web search failed: {e}")

        body = {
            "messages": [model_messages[-1]],
            "project_id": project_id,
            "model_id": "meta-llama/llama-3-2-90b-vision-instruct",
            "decoding_method": "greedy",
            "repetition_penalty": 1,
            "max_tokens": 900
        }

        access_token = get_auth_token(api_key)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.post(
            "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29",
            headers=headers,
            json=body
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        res_content = response.json()['choices'][0]['message']['content']
        st.session_state.messages.append({"role": "assistant", "content": res_content})
        with st.chat_message("assistant"):
            st.write(res_content)

if __name__ == "__main__":
    main()
