#他のファイルからのエージェント
from agents.data_agent import DATAAGENT
from agents.chat_agent import CHATAGENT
from agents.model_agent import MODELAGENT
from agents.report_agent import REPORTWRITER

import google.adk.agents
from google.adk.agents import SequentialAgent

def create_run_state():
    return {
        "status": "running",
        "current_agent": None,
        "retry_count": 0,
        "error": None
    }

run_state = create_run_state()

orchestrator = SequentialAgent(
    name="orchestrator",
        model=Gemini(model=model_name, retry_options=RETRY_OPTIONS),
        description="Use data from the userand call agents to make reports",
        instruction="""
        INSTRUCTIONS:
        - Get Data and model from the CHATAGENT
        - Use DATAAGENT to get data summary
        - Provide MODELAGENT data and get results
        - Provide results to REPORTWRITER and get report.
        - Pass the report to CHATAGENT

        PLOT_OUTLINE:
        { PLOT_OUTLINE? }
        """,
        generate_content_config=types.GenerateContentConfig(
            temperature=0,
        ),
        subagents=[CHATAGENT, DATAAGENT, MODELAGENT, REPORTWRITER,CHATAGENT],
)
