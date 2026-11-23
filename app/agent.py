from google.adk.apps import App
from chat.agent import root_agent as chat_agent

app = App(name="the_full_app", root_agent=chat_agent)