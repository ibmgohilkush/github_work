import streamlit as st
import base64
from PIL import Image
import requests
from bs4 import BeautifulSoup

api_key = st.secrets["IBM_API_KEY"]
project_id = st.secrets["PROJECT_ID"]
serpapi_key = st.secrets["SERPAPI_KEY"]

# getting user info so that we can limit it to location / Seattle for Fox
def get_user_location():
    try:
        res = requests.get("https://ipinfo.io/json")
        data = res.json()
        #data.get( 'city', '') will return the city if available, otherwise an empty string
        #all we need to do is receive it, if we don't get it, doesn't matter, and we just default to US
        return f"{data.get('city', '')}, {data.get('country', '')}"
    except:
        #empty string case
        return "United States"

def search_web(query, max_paragraphs=5):
    search_url = "https://serpapi.com/search"
    params = {
        #this is how to interact with serpapi
        "q": query,
        "api_key": serpapi_key,
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
            page_text = ""
            count = 0
            for p in paragraphs:
                if count >= max_paragraphs:
                    break
                text = p.get_text().strip()
                if text:
                    page_text += text + " "
                    count += 1
            snippets += f"🔹 **{title}**\n{link}\n{page_text.strip()}\n\n"
        except Exception as e:
            snippets += f"🔹 **{title}**\n{link}\n⚠️ Could not fetch page content: {str(e)}\n\n"

    return snippets.strip()

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

def convert_image_to_base64(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode()

def main():
    st.title("Chat with Images + Real-Time Web Search")

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = False

    uploaded_file = st.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        with st.chat_message("user"):
            st.image(image, caption='Uploaded Image', use_column_width=True)
            base64_image = convert_image_to_base64(uploaded_file)
            if not st.session_state.uploaded_file:
                st.session_state.messages.append({
                    "role": "user",
                    "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]
                })
                st.session_state.uploaded_file = True

    for msg in st.session_state.messages[1:]:
        if msg["role"] == "user":
            with st.chat_message("user"):
                if msg["content"][0]["type"] == "text":
                    st.write(msg["content"][0]["text"])
        else:
            st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("Ask me anything...")

    if user_input:
        #for vague queries, we can use it 
        vague_queries = [
            "news", "what's the news", "latest news", "top news",
            "any news", "trending", "what’s happening", "pull up"
        ]
        search_trigger_keywords = ["news", "latest", "trending", "top", "headlines", "update"]

        query_for_search = user_input
        use_auto_search = False

        if user_input.lower().strip() in vague_queries:
            use_auto_search = True
            location = get_user_location()
            query_for_search = f"top news in {location}"

        elif any(kw in user_input.lower() for kw in search_trigger_keywords):
            use_auto_search = True

        message = {"role": "user", "content": [{"type": "text", "text": user_input}]}

        #puttin the web data in it
        if use_auto_search:
            try:
                web_results = search_web(query_for_search)
                if web_results:
                    message["content"].insert(0, {
                        "type": "text",
                        "text": f"Here is live news information:\n\n{web_results}"
                    })
            except Exception as e:
                st.warning(f"Web search failed: {e}")

        st.session_state.messages.append(message)
        st.chat_message("user").write(user_input)

        #inputting that data, and then putting it into json for the model
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

        # sending this over to the llm from model_messages
        body = {
            "messages": [model_messages[-1]],
            "project_id": project_id,
            "model_id": "meta-llama/llama-3-2-90b-vision-instruct",
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

        response = requests.post(
            "https://us-south.ml.cloud.ibm.com/ml/v1/text/chat?version=2023-05-29",
            headers=headers,
            json=body
        )

        if response.status_code != 200:
            raise Exception("Non-200 response: " + str(response.text))

        result = response.json()
        res_content = result["choices"][0]["message"]["content"]

        st.session_state.messages.append({"role": "assistant", "content": res_content})
        st.chat_message("assistant").write(res_content)

if __name__ == "__main__":
    main()
