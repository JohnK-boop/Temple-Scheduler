# Model agent - John
# not hooked up to orchestrator yet

from google.adk.agents.llm_agent import Agent
from .model_tools import list_model_options, train_model, evaluate_model, explain_model, predict

model_agent = Agent(
    model="gemini-3.5-flash",
    name="model_agent",
    description="Trains, evaluates and explains BigQuery ML models.",
    instruction="""
You build machine learning models in BigQuery. You will be given a table and a target column.

First figure out if the target is a category (classification) or a number (regression).
Use list_model_options to see what models you can use, and pick 2.
Train both with train_model. Don't use ID columns or columns that give away the answer
(for the student data that is G1, G2 and G3).
Then use evaluate_model and explain_model on both.
Pick the better one using roc_auc for classification or mean_absolute_error for regression.
Don't just go off accuracy.

At the end report which models you trained, their scores, which one was best,
the top features, and why you made your choices.
""",
    tools=[list_model_options, train_model, evaluate_model, explain_model, predict],
)
