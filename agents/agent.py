from google.adk.agents.llm_agent import Agent
from google.adk import Workflow
from google.cloud import bigquery
from google.adk.tools import google_search

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
When necessary, you can use the \'use_bigquery\' tool (which takes a query as its 
argument) to assist with your task.
Use the 'google_search' tool to consult bigquery documentation if you aren't
sure how to perform any operations.

Examine the 'input' dataset. The 'input' dataset is the data for a machine
learning application. You will be told which features in the dataset are the
targets, all others can be used as input to the machine learning model. 

Create the new dataset 'input_engineered'. This will store the results of your
feature engineering.

For each feature:
1. determine whether it should be included as input to the machine learning model.
Consider criteria such as relevance, overlap with other features, and effect
size.

2. determine whether the data should be transformed in some way. For example,
   numeric data might need to be normalized, while categorical data might need
   to be encoded using either numerical or one-hot encodings.

3. If you have determined that the data should be included, copy it from the
   input dataset to the input_engineered dataset while applying the determined
   transformation (if any).

After this has been performed for all features, determine whether any computed
features should also be included. This could include logs, roots or other
functions applied to existing numerical features, as well as features calculated
from multiple other features such as products or sums. Finally, consider whether
numeric data should be binned or bucketed. When deciding whether to create a
computed feature, use criteria of relevance, usefulness and overlap with
previous features. Create the computed features in the input_engineered dataset.

Finally, report all the features chosen and decisions made, as well as the
reasoning behind those decisions.
""",
    tools = [use_bigquery, google_search]
)

root_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", feature_engineer)
    ]
)
