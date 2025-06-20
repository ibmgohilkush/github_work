import streamlit as st
import base64
from PIL import Image
import requests

api_key = st.secrets["IBM_API_KEY"]
project_id = st.secrets["PROJECT_ID"]

#the code can only understand it in base 64, so you have to convert it initially
    #this is done by getting the value of the file, then encoding in b64.encode, then decode that after to get the image
def convert_image_to_base64(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    base64_image = base64.b64encode(bytes_data).decode()
    return base64_image

def get_auth_token(api_key):
    auth_url = "https://iam.cloud.ibm.com/identity/token"
    headers = {
        #code can only be sent in JSON format, and the content is being written as "form data" content
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    data = {
        #this is the POST format, grant type says that we are using an api key to authorize   
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": api_key
    }
    #we don't want to verify, that does SSL which is too much for dev testing, just the post response
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

    #posting in json 
    response = requests.post(url, headers=headers, json=body)
    if response.status_code != 200:
        raise Exception(f"Non-200 response: {response.text}")
    
    #choices is the text, the key to the values we want, where we then parse that by the messages tag, and get the content 
    return response.json()['choices'][0]['message']['content']

def main():
    st.title("Chat with Images")

    #initializing all messages, kept in a list format 
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_file" not in st.session_state:
        st.session_state.uploaded_file = False
    if "image_analyzed" not in st.session_state:
        st.session_state.image_analyzed = False

    #the first UI seen to interface/add files
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        base64_image = convert_image_to_base64(uploaded_file)

        with st.chat_message("user"):
            #this is just displaying the image, nothing else, for the user
            st.image(image, caption="Uploaded Image", use_column_width=True)

        if not st.session_state.uploaded_file:
            #it needs to be in the message history to naalyze it, so kepe it like that, and then display the content as the image
            st.session_state.messages.append({
                "role": "user",
                "content": [{"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}]
            })
            st.session_state.uploaded_file = True
            st.session_state.image_analyzed = False

        #one anlaysis held by a boolean that's changed after
        if not st.session_state.image_analyzed:
            system_prompt = {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Based on this image, ask 3 thought-provoking questions about its content, atmosphere, or elements you notice."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
                ]
            }
            #loading screen until the code computes from the query model
                #where the query function is just sending the message with the authorization we have
            with st.spinner("Generating questions..."):
                ai_response = query_model([system_prompt])


            #then, it just adds the message it develops as the response written from the "assistant", not "user", role 
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

            st.session_state.image_analyzed = True

    #keeping the previous chat history 
    for msg in st.session_state.messages[1:]:
        if msg['role'] == "user":
            with st.chat_message("user"):
                if isinstance(msg['content'], list):
                    for item in msg['content']:
                        if item['type'] == "text":
                            st.write(item['text'])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])

    #then, keep the function of chat input ready 
    user_input = st.chat_input("Type your message here...")
    if user_input:
        #add the message input to the response model, and then append/write that in 
        new_msg = {"role": "user", "content": 
                   [{"type": "text", "text": user_input}]}
        st.session_state.messages.append(new_msg)
        st.chat_message("user").write(user_input)

        #call the function, and keep that message response in json
        ai_reply = query_model([new_msg])
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        with st.chat_message("assistant"):
            st.write(ai_reply)

if __name__ == "__main__":
    main()
