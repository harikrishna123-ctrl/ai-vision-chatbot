
from google import genai
from google.genai import types
import streamlit as st

try:
    from twilio.rest import Client  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - dependency may be absent in local/dev envs
    Client = None

from prompts import SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
TWILIO_ACCOUNT_SID = st.secrets["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = st.secrets["TWILIO_AUTH_TOKEN"]
@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key=GEMINI_API_KEY)
gemini_client = get_gemini_client()
MODEL_NAME = "gemini-2.5-flash"

def send_whatsapp(whatsapp_number, name, summary):
    if Client is None:
        return False, "Twilio is not installed. Please install the package to send WhatsApp messages."

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Hi {name},\n\n{summary.strip() or 'No summary available.'}",
            from_=f"whatsapp:{st.secrets['TWILIO_WHATSAPP_NUMBER']}",
            to=f"whatsapp:{whatsapp_number}",
        )
        return True, message.sid
    except Exception as error:
        return False, str(error)


def send_message(whatsapp_number, name, summary):
    return send_whatsapp(whatsapp_number, name, summary)


def render_messages(messages):
    with st.chat_message(messages["role"]):
        if messages["kind"]=="text":
            st.write(messages["content"])
        elif messages["kind"]=="image":
            st.image(messages["content"])
def add_messages(role,kind,content):
    st.session_state.messages.append({"role":role,"kind":kind,"content":content})
    render_messages(st.session_state.messages[-1])  # Render only the last message

def ask_gemini(parts):
    try:
        return st.session_state.chat.send_message(parts).text
    except Exception as error:
        return f"Sorry,something went wrong: {error}"

#step 1: onboarding(username and phone)
if not st.session_state.get("onboarded", False):
    st.title("MacroSnap")
    st.caption("snap it.Track it.Text your thoughts and see the results")
    with st.form("Onboarding form"):
        name=st.text_input("Enter your name") #Harikrishna
        whatsapp_number=st.text_input("whatsapp number (with country code)",
        placeholder="+91xxxxxxxxxx",
        help="This is the number Macrosnap will text your summary to.",)
        submitted = st.form_submit_button("Let's go")

    if submitted:
        if not name.strip() or not whatsapp_number.strip():
            st.warning("Please fill in both your name and whatsapp number.")
        else:
            st.session_state.name = name.strip()
            st.session_state.whatsapp_number = whatsapp_number.strip()
            st.session_state.chat = gemini_client.chats.create(
                model=MODEL_NAME,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            st.session_state.messages = []
            st.session_state.onboarded = True
            st.rerun()
    st.stop()
# create a chat interface
header_col,button_col=st.columns([5,2],vertical_alignment="center")
with header_col:
    st.title("MacroSnap")
    st.caption("snap it.Track it.Text your thoughts and see the results")
with button_col:
    send_disabled=len(st.session_state.messages)<=1
    if st.button("Send to Whatsapp",disabled=send_disabled,use_container_width=True):
       with st.spinner("Summarizing your day..."): 
           summary=ask_gemini([SUMMARY_REQUEST_PROMPT])
       success,info=send_whatsapp(st.session_state.whatsapp_number,st.session_state.name,summary) 
       if success:
            st.success("Sent! Check your whatsapp.") 
       else:
            st.error(f"Couldn't send that: {st.info}")
st.caption(f"Logged in as {st.session_state.name}- updates to go {st.session_state.whatsapp_number}.")
if not st.session_state.messages:
    add_messages("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(name=st.session_state.name))
else:
    for message in st.session_state.messages:
        render_messages(message)     
user_input=st.chat_input(
    "Ask a question,or attach a photo of your meal", 
    accept_file=True,
    file_type=["jpg","jpeg","png"],

) 
if user_input:
    photo=user_input.files[0] if user_input.files else None 
    text=user_input.text
    parts=[]

    if photo is not None:
        photo_bytes=photo.getvalue()
        add_messages("user","image",photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes,mime_type=photo.type))
    if text:
        add_messages("user","text",text)
        parts.append(text)

    elif photo is not None:
        parts.append("What is the meal? Give me the calories and macros.") 
    with st.spinner("Crunching the numbers..."):
        answer=ask_gemini(parts)
    add_messages("assistant","text",answer)




