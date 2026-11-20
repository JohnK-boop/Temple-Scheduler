from google.adk.agents.llm_agent import Agent
from google.adk import Workflow
from google.cloud import bigquery
import pandas as pd

import bigframes.pandas as bpd

import vertexai


project_id = "temple-scheduler-cisproj"
dataset_id = "agent_data"
input_table_id = "input"
output_table_id = "input_engineered"

bigquery_client = bigquery.Client(project=project_id)
bigquery_client.create_table(f"{dataset_id}.{input_table_id}", exists_ok=True)
bigquery_client.create_table(f"{dataset_id}.{output_table_id}", exists_ok=True)

bpd.options.bigquery.project = project_id
input_df = bpd.read_gbq(f"{project_id}.{dataset_id}.{input_table_id}")

def list_input_columns():
    return {str(r[0]): str(r[1]) for r in zip(input_df.columns, input_df.dtypes)}

def normalize_column(column_name: str):
    max: float = input_df[column_name].max()
    min: float= input_df[column_name].max()

    @bpd.udf(dataset=dataset_id, name="normalize")
    def normalize(x: float) -> float:
        return (x - min) / (max - min)
    input_df[column_name].apply(normalize)
    # why isn't the column being updated in bigquery?
    return {"success": True}

client = vertexai.init(
    project='temple-scheduler-cisproj',
    location='us-central1'
)


feature_engineer = Agent(
    model='gemini-3.5-flash',
    name='feature_engineer',
    description='Performs feature engineering and ingests data into BigQuery.',
    instruction=""" 
    You have access to the following tools:

    'list_input_columns' - list the columns in the input table, along with
    their types

    'normalize_column' - normalize the column's contents from 0 to 1.
    """,
#     instruction="""
# When necessary, you can use the \'use_bigquery\' tool (which takes a query as its 
# argument) to assist with your task.
# Use the 'google_search' tool to consult bigquery documentation if you aren't
# sure how to perform any operations.
#
# Examine the 'input' dataset. The 'input' dataset is the data for a machine
# learning application. You will be told which features in the dataset are the
# targets, all others can be used as input to the machine learning model. 
#
# Create the new dataset 'input_engineered'. This will store the results of your
# feature engineering.
#
# For each feature:
# 1. determine whether it should be included as input to the machine learning model.
# Consider criteria such as relevance, overlap with other features, and effect
# size.
#
# 2. determine whether the data should be transformed in some way. For example,
#    numeric data might need to be normalized, while categorical data might need
#    to be encoded using either numerical or one-hot encodings.
#
# 3. If you have determined that the data should be included, copy it from the
#    input dataset to the input_engineered dataset while applying the determined
#    transformation (if any).
#
# After these steps have been performed for all features, determine whether any computed
# features should also be included. This could include logs, roots or other
# functions applied to existing numerical features, as well as features calculated
# from multiple other features such as products or sums. Finally, consider whether
# numeric data should be binned or bucketed. When deciding whether to create a
# computed feature, use criteria of relevance, usefulness and overlap with
# previous features. Create the computed features in the input_engineered dataset.
#
# Finally, report all the features chosen and decisions made, as well as the
# reasoning behind those decisions.
# """,
    tools = [list_input_columns, normalize_column]
)

data_agent = Workflow(
    name="root_agent",
    edges=[
        ("START", feature_engineer)
    ]
)
