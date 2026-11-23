from google.adk.agents.llm_agent import Agent
from agents.model_tools import list_model_options
from chat.tools import save_user_csv, read_csv_get_all_key, select_target
from orchestrator.orchestrator import orchestrator
from orchestrator.shared_key import CSV_URI, CSV_NAME
from google.adk.tools.agent_tool import AgentTool
root_agent = Agent(
    model="gemini-3.5-flash",
    name="root_agent",
    description="Root agent",
    instruction="""
    You are a data analysis agent. You can help the user to analyze their csv, 
    
    ## Current state:
    - Upload CSV: {csv_name?}
    (If this is empty it means the user has not uploaded a CSV yet. You should ask them to upload one.)
    - Target column: {target_column?}
    (If this is empty it means the user has not selected a target column yet. You should ask them to select one.)
    - Train model optional: {model_type?}
    (If this is empty it means the user has not selected a model to train yet. You should ask them to select one if they want to train a model.)
    
    
    ## Workflow
    1. Ask the user to upload a CSV file if they haven't done so.
    2. Once the CSV is uploaded, read the csv and get the key (column names) and ask the user to select a target column for analysis.
    3. Once the target column is selected, you can perform analysis on the data by calling the orchestrator agent.
    """,
    tools=[
        list_model_options,
        read_csv_get_all_key,
        select_target,
        AgentTool(agent=orchestrator),

    ],
    before_agent_callback=save_user_csv,

)


