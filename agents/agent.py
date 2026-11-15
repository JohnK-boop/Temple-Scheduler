from google.adk.agents.llm_agent import Agent
from google.adk import Workflow
from google.cloud import bigquery

import vertexai

bigquery_client = bigquery.Client(project="temple-scheduler-cisproj")

def format_row(row):
    return ",".join([x[0] + ": " + str(x[1]) for x in row.items()])

def use_bigquery(query: str):
    query_job = bigquery_client.query(query)
    rows = query_job.result()
    return { "rows": [format_row(r) for r in rows] }


client = vertexai.init(
    project='temple-scheduler-cisproj',
    location='us-central1'
)


feature_engineer = Agent(
    model='gemini-3.5-flash',
    name='feature_engineer',
    description='Performs feature engineering and ingests data into BigQuery.',
    instruction="""
Helpfully answer the user's questions. 
When necessary, you can use the \'use_bigquery\' tool (which takes a query as its 
argument) to assist the user with their task.
""",
    tools = [use_bigquery]
)

root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", feature_engineer)
    ]
)
