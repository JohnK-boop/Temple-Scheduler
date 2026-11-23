#from google.adk.apps import App
#from chat.agent import root_agent as chat_agent

# TODO: switch to the chate agent, once added in repo
#from .model_agent import model_agent

#root_agent = chat_agent

#app = App(
#    name="agents",
#    root_agent=root_agent
#)

from google.adk.apps import App
from chat.agent import root_agent as chat_agent

# TODO: switch to chat agent once orchestrator.py imports cleanly:
# from chat.agent import root_agent as chat_agent
root_agent = chat_agent

app = App(name="agents", root_agent=root_agent)