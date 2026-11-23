#imports
import asyncio
import json
import time
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from .shared_key import RUN_HISTORY

# test or real agent
USE_TEST_AGENTS = False

if USE_TEST_AGENTS:
    from . import testagent
    data_agent = testagent.data_agent()
    model_agent = testagent.model_agent()
    report_writer = testagent.report_writer()
else:  # REAL AGENTS
    from agents.data_agent import feature_engineer as data_agent
    from agents.model_agent import model_agent
    from agents.results_limitations.agent import results_limitations_agent as report_writer

    # save result
    data_agent.name = "data_agent"
    data_agent.output_key = "data_result"
    model_agent.name = "model_agent"
    model_agent.output_key = "model_result"
    report_writer.name = "report_writer"
    report_writer.output_key = "report"

# limit of try
MAX_ATTEMPTS = 3 
RETRY_WAIT_SEC = 0.1 

#post note
def _text_event(author, text, state_delta=None):
    """Make one 'notice card' (Event) with a message and optional state to save."""
    return Event(
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
    )

#get note
def _event_text(event):
    """Take the text out of an Event (empty string if there is none)."""
    if not event.content or not event.content.parts:
        return ""
    return "".join(p.text for p in event.content.parts
                   if p.text and not getattr(p, "thought", False))


# object orchestrator
class Orchestrator(BaseAgent):
    """Runs sub_agents in order.
    Success -> returns {"status": "success", "report": <report text>}
    Failure -> returns {"status": "failed", "history": [<what happened>]}"""
    #get note(adkが呼ぶ）
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        history = []   # the teacher's notebook
        report = ""
        for sub in self.sub_agents:                         # one agent at a time
            for attempt in range(1, MAX_ATTEMPTS + 1):     # up to MAX_ATTEMPTS tries
                text_of_this_agent = ""
                history.append({"agent": sub.name, "status": "running",
                                "attempt": attempt, "at": time.time()})
                try:
                    async for event in sub.run_async(ctx):  # let the agent run
                        yield event
                        text = _event_text(event)
                        if text:
                            text_of_this_agent = text
                except Exception as e:                      # the agent failed
                    history.append({"agent": sub.name, "status": "failed",
                                    "attempt": attempt, "at": time.time(), "error": str(e)})
                    if attempt < MAX_ATTEMPTS:
                        await asyncio.sleep(RETRY_WAIT_SEC)
                        continue                            # try again
                    # failed every time -> return the history and stop
                    result = json.dumps({"status": "failed", "history": history}, ensure_ascii=False)
                    yield _text_event(self.name, result, {RUN_HISTORY: history})
                    return
                history.append({"agent": sub.name, "status": "done",
                                "attempt": attempt, "at": time.time()})
                report = text_of_this_agent                 # the last agent's text = the report
                break                                       # success -> next agent
        # everyone finished -> return the report
        result = json.dumps({"status": "success", "report": report}, ensure_ascii=False)
        yield _text_event(self.name, result, {RUN_HISTORY: history})


#orchestrator
orchestrator = Orchestrator(
    name="orchestrator",
    description="Run data -> model -> report. Returns a JSON string: "
                "{'status': 'success', 'report': ...} or {'status': 'failed', 'history': [...]}. "
                "Call this once the user's request is ready.",
    sub_agents=[data_agent, model_agent, report_writer],
)
