from google.adk.agents.llm_agent import Agent
from google.adk import Workflow
from google.cloud import bigquery

import vertexai


project_id = "temple-scheduler-cisproj"
dataset_id = "agent_data"
input_table_id = "input"
output_table_id = "input_engineered"

bigquery_client = bigquery.Client(project=project_id)
bigquery_client.create_table(f"{dataset_id}.{input_table_id}", exists_ok=True)
bigquery_client.create_table(f"{dataset_id}.{output_table_id}", exists_ok=True)


def prepare():
    delete_table_job = bigquery_client.query(f"""
    DROP TABLE IF EXISTS {dataset_id}.{input_table_id};
                                             """)
    delete_table_job.result()
    delete_table_job = bigquery_client.query(f"""
    DROP TABLE IF EXISTS {dataset_id}.temp_table;
                                             """)
    delete_table_job.result()
    delete_table_job = bigquery_client.query(f"""
    DROP TABLE IF EXISTS {dataset_id}.{output_table_id};
                                             """)
    delete_table_job.result()
    
    create_id_column_job = bigquery_client.query(f"""
    CREATE TABLE {dataset_id}.{input_table_id}
    (
        row_id INT GENERATED ALWAYS AS IDENTITY(START WITH 0 INCREMENT BY 1)
    );
                                                 """)
    create_id_column_job.result()
    # load data from csv, insert row_id column
    load_csv_job = bigquery_client.query(f"""
    LOAD DATA OVERWRITE {dataset_id}.temp_table
    FROM FILES (
        format = 'CSV',
        uris = ['gs://cis3203-uploads/student-por.csv']
    );
                                         """)
    load_csv_job.result()

    table_column_names = bigquery_client.query(f"""
    SELECT column_name, data_type FROM {dataset_id}.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'temp_table';
                                               """)
    names = list(table_column_names.result())
    for name in names:
        j = bigquery_client.query(f"""
        ALTER TABLE {dataset_id}.{input_table_id}
        ADD COLUMN {name[0]} {name[1]};
                                  """)
        j.result()

    copy_columns_job = bigquery_client.query(f"""
    INSERT INTO {dataset_id}.{input_table_id} ({",".join([n[0] for n in names])})
    SELECT {",".join([n[0] for n in names])} FROM {dataset_id}.temp_table
                                             """)
    copy_columns_job.result()

    create_id_column_job = bigquery_client.query(f"""
    CREATE TABLE {dataset_id}.{output_table_id}
    (
        row_id INT
    );
                                                 """)
    create_id_column_job.result()

    insert_row_ids_job = bigquery_client.query(f"""
    INSERT INTO {dataset_id}.{output_table_id} (row_id)
    SELECT row_id FROM {dataset_id}.{input_table_id};
                                               """);
    insert_row_ids_job.result()
    return { "success": True }

def list_input_columns():
    table_column_names = bigquery_client.query(f"""
    SELECT column_name, data_type FROM {dataset_id}.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{input_table_id}';
                                               """)
    names = list(table_column_names.result())
    return {
        "success": True,
        "names": ["{\""+n[0]+"\":\""+n[1]+"}" for n in names if n[0] != "row_id"]
    }

def normalize_column(column_name: str):
    
    job = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name + "_normalized"};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name + "_normalized"} FLOAT64;

    UPDATE 
        {dataset_id}.{output_table_id} 
        
    SET {column_name + "_normalized"} = 
        ({input_table_id}.{column_name} 
            - (SELECT MIN({input_table_id}.{column_name}) FROM {dataset_id}.{input_table_id})
         ) 
        / (
            (SELECT MAX({input_table_id}.{column_name}) FROM {dataset_id}.{input_table_id})
            - (SELECT MIN({input_table_id}.{column_name}) FROM {dataset_id}.{input_table_id})
        )
        
    FROM ((SELECT row_id, {column_name + "_normalized"} FROM {dataset_id}.{output_table_id}) AS output
        JOIN {dataset_id}.{input_table_id} 
        ON {input_table_id}.row_id 
        = output.row_id)
    WHERE {output_table_id}.row_id = {input_table_id}.row_id;
                                """)
    job.result()

    return {"success": True}

def copy_column(column_name):
    job1 = bigquery_client.query(f"""
    SELECT data_type FROM {dataset_id}.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{input_table_id}'
        AND COLUMN_NAME = '{column_name}'
    LIMIT 1;
                                 """)
    data_type = list(job1.result())[0][0]

    job2 = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name} {data_type};

    UPDATE {dataset_id}.{output_table_id}
    SET {column_name} = {input_table_id}.{column_name}
    FROM (
        (SELECT row_id, {column_name} FROM {dataset_id}.{output_table_id}) AS output
        JOIN {dataset_id}.{input_table_id} 
        ON {input_table_id}.row_id 
        = output.row_id
    )
    WHERE {output_table_id}.row_id = {input_table_id}.row_id
                                """)
    job2.result()
    return { "success": True,
             "name": column_name,
            "type": data_type
    }

def onehot_encode_column(column_name):
    pass

def logarithm_column(column_name):
    job = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name + "_log"};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name + "_log"} FLOAT64;

    UPDATE 
        {dataset_id}.{output_table_id} 
        
    SET {column_name + "_log"} = 
        LOG({input_table_id}.{column_name})
        
    FROM ((SELECT row_id, {column_name + "_log"} FROM {dataset_id}.{output_table_id}) AS output
        JOIN {dataset_id}.{input_table_id} 
        ON {input_table_id}.row_id 
        = output.row_id)
    WHERE {output_table_id}.row_id = {input_table_id}.row_id;
                                """)
    job.result()

    return {"success": True}

def feature_cross(column_name_a, column_name_b):
    pass

def feature_difference(column_name_a, column_name_b):
    pass

def impute_mean(column_name):
    job = bigquery_client.query(f"""
    UPDATE {dataset_id}.{input_table_id}
    SET {column_name} = (SELECT AVG({column_name}) FROM {dataset_id}.{input_table_id})
    WHERE {column_name} IS NULL;
                               """)
    job.result()

    return { "success": True }

def impute_mode(column_name):
    job1 = bigquery_client.query(f"""

    UPDATE {dataset_id}.{input_table_id}
    SET {column_name} = 
        (SELECT {column_name} AS mode
        FROM {dataset_id}.{input_table_id}
        GROUP BY {column_name}
        ORDER BY COUNT(*) DESC
        LIMIT 1)
    WHERE {column_name} IS NULL;
                                """)
    job1.result()


    return {
            "success": True
    }

def has_null(column_name):
    job = bigquery_client.query(f"""
    SELECT {column_name} 
    FROM {dataset_id}.{input_table_id}
    WHERE {column_name} IS NULL;
                                   """)
    rows = list(job.result())
    return {
        "has_nulls": len(rows) > 0
    }

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
    tools = [prepare, list_input_columns, normalize_column, copy_column,
             onehot_encode_column, logarithm_column, feature_cross,
             feature_difference, impute_mean, impute_mode,
             has_null]
)

data_agent = Workflow(
    name="data_agent",
    edges=[
        ("START", feature_engineer)
    ]
)
