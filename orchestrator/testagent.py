from google.adk.agents import BaseAgent
from google.adk.events import Event
from google.genai import types

class PlaceholderAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part(text=f"{self.name} finished")],
            ),
        )

def chat_agent():
    chat_agent = PlaceholderAgent(name="chat_agent", description="Collect the analysis request.")
    return chat_agent

def data_agent():
    data_agent = PlaceholderAgent(name="data_agent", description="Prepare the table.")
    return data_agent

def model_agent():
    model_agent = PlaceholderAgent(name="model_agent", description="Train and evaluate the model.")
    return model_agent

def report_writer():
    report_writer = PlaceholderAgent(name="report_writer", description="Write the report.")
    return report_writer