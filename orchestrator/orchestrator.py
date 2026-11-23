import asyncio
import time
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from .shared_key import RUN_HISTORY

#agent側のorchestrator
#test or real agents
USE_TEST_AGENTS = False

if USE_TEST_AGENTS:
    from . import testagent
    data_agent = testagent.data_agent()
    model_agent = testagent.model_agent()
    report_writer = testagent.report_writer()
else:#REAL AGNETS
    from agents.data_agent import feature_engineer as data_agent
    from agents.model_agent import model_agent
    from agents.results_limitations.agent import results_limitations_agent as report_writer

MAX_ATTEMPTS = 3      # How many times the agents are going to proceed when it fails
RETRY_WAIT_SEC = 0.1 

def _text_event(author, text, state_delta=None):
    return Event(
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
    )


class Orchestrator(BaseAgent):
    "notes the history"
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        history = []
        done = []
        for sub in self.sub_agents:
            for attempt in range(1, MAX_ATTEMPTS + 1):
                history.append({"agent": sub.name, "status": "running",
                                "attempt": attempt, "at": time.time()})
                try:
                    async for event in sub.run_async(ctx):
                        yield event
                except Exception as e:
                    history.append({"agent": sub.name, "status": "failed",
                                    "attempt": attempt, "at": time.time(), "error": str(e)})
                    if attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(RETRY_WAIT_SEC)
                        continue  # retry
                    msg = (f"Process stoped. Done: {', '.join(done) if done else 'None'} / "
                           f"Fail: {sub.name}({attempt} attempts: {type(e).__name__}: {e})")
                    yield _text_event(self.name, msg, {RUN_HISTORY: history})
                    return
                history.append({"agent": sub.name, "status": "done",
                                "attempt": attempt, "at": time.time()})
                done.append(sub.name)
                break  # done to the next person
        yield Event(author=self.name, actions=EventActions(state_delta={RUN_HISTORY: history}))
sub_agents = [data_agent, model_agent, report_writer]

orchestrator = Orchestrator(
    name="orchestrator",
    description="Run data -> model -> report and return the final report. Make a report by coordinating agents, share information between them, and record how far it has been done or failed.",
    sub_agents = sub_agents
)
