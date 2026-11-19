import asyncio
import time
from typing import AsyncGenerator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.genai import types
from .shared_key import RUN_HISTORY

#agent側のorchestrator
from .shared_key import log_start, log_end  
#test用のエージェント切り替え可
USE_TEST_AGENTS = True

if USE_TEST_AGENTS:
    from . import testagent
    data_agent = testagent.data_agent()
    model_agent = testagent.model_agent()
    report_writer = testagent.report_writer()
else:#他のファイルからのエージェント
    from agents.data_agent import data_agent
    from agents.model_agent import model_agent
    from agents.report_agent import report_writer

MAX_ATTEMPTS = 3      # 1つのエージェントを最大何回まで試すか（最初の1回を含む）
RETRY_WAIT_SEC = 0.1 

def _text_event(author, text, state_delta=None):
    return Event(
        author=author,
        content=types.Content(role="model", parts=[types.Part(text=text)]),
        actions=EventActions(state_delta=state_delta or {}),
    )


class Orchestrator(BaseAgent):
    """sub_agents を順に実行する。LLMは使わない。失敗したら「どこまで終わったか」を返して止まる。"""
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
                        continue  # もう一回走る
                    msg = (f"処理が途中で止まりました。完了: {', '.join(done) if done else 'なし'} / "
                           f"失敗: {sub.name}（{attempt}回試しました: {type(e).__name__}: {e}）")
                    yield _text_event(self.name, msg, {RUN_HISTORY: history})
                    return
                history.append({"agent": sub.name, "status": "done",
                                "attempt": attempt, "at": time.time()})
                done.append(sub.name)
                break  # 成功したので次の人へ
        yield Event(author=self.name, actions=EventActions(state_delta={RUN_HISTORY: history}))
sub_agents = [data_agent, model_agent, report_writer]

orchestrator = Orchestrator(
    name="orchestrator",
    description="Run data -> model -> report and return the final report. Make a report by coordinating agents, share information between them, and record how far it has been done or failed.",
    sub_agents = sub_agents
)
# root_agent = orchestrator
#どこで結果が正しいか確認するんだろう
#tools=[AgentTool(agent=orchestrator)]＃Chatに入れてもらわないと