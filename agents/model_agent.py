# Model agent - John

from google.adk.agents.llm_agent import Agent
from .model_tools import train_model, evaluate_model, explain_model, predict

model_agent = Agent(
    model="gemini-3.5-flash",
    name="model_agent",
    description="Trains, evaluates and explains BigQuery ML models using a config it is given.",
    instruction="""
You build machine learning models in BigQuery using a config you are given.
You do not make any choices yourself. Use the config exactly as given.

The config will have:
- table: the table to train on
- target: the column to predict
- model_type: the model to train
- model_name: the name to save the model as 

Steps:
1. Train the model with train_model using the config values.
2. Run evaluate_model on it.
3. Run explain_model on it.

If the config is missing something, stop and say which value is missing.
If a tool returns an error, stop and send the error exactly as it was returned.
Don't guess, fill in missing values, or try to fix it yourself.

At the end return only:
- the config you used
- the scores from evaluate_model
- the top features from explain_model
Don't interpret the results or make recommendations. Another agent does that.
""",
    output_key="model_result",
    tools=[train_model, evaluate_model, explain_model, predict],
)
