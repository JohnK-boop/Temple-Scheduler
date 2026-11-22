# Model agent - John

from google.adk.agents.llm_agent import Agent
from .model_tools import train_model, evaluate_model, explain_model, predict

model_agent = Agent(
    model="gemini-3.5-flash",
    name="model_agent",
    description="Trains, evaluates and explains a BigQuery ML model using the data agent's table and the user's chosen target and model type.",
    instruction="""
You build machine learning models in BigQuery. You do not make any choices yourself.

What the data agent prepared:
{data_result?}

The column the user wants to predict:
{target_column?}

The model type the user chose:
{model_type?}

From these, take:
- table: the table the data agent created
- target: the column the user wants to predict
- model_type: the model type the user chose

Steps:
1. Train with train_model using those values. Leave model_name blank.
2. Run evaluate_model on the model_name that train_model returns.
3. Run explain_model on it.

If any of the three values is missing, stop and say which one.
If a tool returns an error, stop and send the error exactly as it was returned.

At the end return only: the values you used, the scores from evaluate_model,
and the top features from explain_model. Don't interpret the results.
""",
    output_key="model_result",
    tools=[train_model, evaluate_model, explain_model, predict],
)