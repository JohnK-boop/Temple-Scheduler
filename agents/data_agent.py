from google.adk.agents.llm_agent import Agent
from google.adk import Workflow
from google.cloud import bigquery
from google.adk.tools import ToolContext
from orchestrator.shared_key import CSV_URI, TARGET_COLUMN

import vertexai


project_id = "temple-scheduler-cisproj"
dataset_id = "agent_data"
input_table_id = "input"
output_table_id = "input_engineered"

bigquery_client = bigquery.Client(project=project_id)
bigquery_client.create_table(f"{dataset_id}.{input_table_id}", exists_ok=True)
bigquery_client.create_table(f"{dataset_id}.{output_table_id}", exists_ok=True)

"""
gets the name of the target column. no parameters.
"""
def target_column(tool_context: ToolContext):
    return { "target": tool_context.state[TARGET_COLUMN] }

"""
Prepares the environment for feature engineering work to be performed. 
Does not take any arguments. Using this tool a second time may destroy existing
feature engineering work.
"""
def prepare(tool_context: ToolContext):
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
        uris = ['{tool_context.state[CSV_URI]}']
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

"""
Lists the names and datatypes of all the columns in the input table.
Does not take any arguments.
"""
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

"""
Lists the names and datatypes of all the columns in the output table.
Does not take any arguments.
"""
def list_output_columns():
    table_column_names = bigquery_client.query(f"""
    SELECT column_name, data_type FROM {dataset_id}.INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = '{output_table_id}';
                                               """)
    names = list(table_column_names.result())
    return {
        "success": True,
        "names": ["{\""+n[0]+"\":\""+n[1]+"}" for n in names if n[0] != "row_id"]
    }

"""
For the named column in the input table, creates a column in the output table
that stores the values from the input column normalized to the range 0-1. Does
not work for data that is not numeric.
@param column_name: the name of the column to normalize.
"""
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

"""
Copies a column of data from the input table to the output table unchanged.
@param column_name: the name of the column to copy
"""
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

"""
Places a numerical encoding of string data in the input column into the output
table. Each unique string value in the column is given its own integer to
represent it.
@param column_name: the name of the column to encode
"""
def numerical_encode_column(column_name):
    job1 = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name + "_numeric"};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name + "_numeric"} INT64;
    SELECT {column_name} 
    FROM {dataset_id}.{input_table_id} 
    GROUP BY {column_name}
                                 """)
    variants = job1.result()
    for num, v in enumerate(variants):
        jobi = bigquery_client.query(f"""
        UPDATE {dataset_id}.{output_table_id}
        SET {column_name + "_numeric"} = {num}
        FROM ((SELECT row_id, {column_name + "_numeric"} FROM {dataset_id}.{output_table_id}) AS output
            JOIN {dataset_id}.{input_table_id} 
            ON {input_table_id}.row_id 
            = output.row_id)
        WHERE {output_table_id}.row_id = {input_table_id}.row_id 
            AND {input_table_id}.{column_name} = "{v[0]}";
                                     """)
        jobi.result()
    return {"success": True}

"""
For the named column in the input table, creates a column in the output table
that stores the logarithm of the values from the input column. Does
not work for data that is not numeric.
@param column_name: the column to take the logarithm of.
"""
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

"""
Creates a new calculated feature that is the cross of two existing features.
The values in the new feature are the product of the values of the source
features. Only works for numeric features.
@param column_name_a: the name of the first feature to be crossed.
@param a_is_from_input: boolean value indicating whether the first feature to be
crossed should come from the input table or the output table.
@param column_name_b: the name of the second feature to be crossed.
@param b_is_from_input: boolean value indicating whether the second feature to be
crossed should come from the input table or the output table.
"""
def feature_cross(column_name_a, a_is_from_input, column_name_b, b_is_from_input):
    job = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name_a + "_cross_" + column_name_b};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name_a + "_cross_" + column_name_b} FLOAT64;

    UPDATE {dataset_id}.{output_table_id}
    SET {column_name_a + "_cross_" + column_name_b} =
        {input_table_id if a_is_from_input else output_table_id}.{column_name_a}
        *
        {input_table_id if b_is_from_input else output_table_id}.{column_name_b}
    FROM ({dataset_id}.{output_table_id} AS output
          JOIN {dataset_id}.{input_table_id}
          ON {input_table_id}.row_id
          = output.row_id)
    WHERE {output_table_id}.row_id = {input_table_id}.row_id;
                                """)
    job.result()

    return { "success": True }

"""
Creates a new calculated feature that is the difference of two existing features.
Only works for numeric features.
@param column_name_a: the name of the first feature to be crossed.
@param a_is_from_input: boolean value indicating whether the first feature to be
crossed should come from the input table or the output table.
@param column_name_b: the name of the second feature to be crossed.
@param b_is_from_input: boolean value indicating whether the second feature to be
crossed should come from the input table or the output table.
"""
def feature_difference(column_name_a, a_is_from_input, column_name_b,
                       b_is_from_input):
    job = bigquery_client.query(f"""
    ALTER TABLE {dataset_id}.{output_table_id}
    DROP COLUMN IF EXISTS {column_name_a + "_diff_" + column_name_b};
    ALTER TABLE {dataset_id}.{output_table_id}
    ADD COLUMN {column_name_a + "_diff_" + column_name_b} FLOAT64;

    UPDATE {dataset_id}.{output_table_id}
    SET {column_name_a + "_diff_" + column_name_b} =
        {input_table_id if a_is_from_input else output_table_id}.{column_name_a}
        -
        {input_table_id if b_is_from_input else output_table_id}.{column_name_b}
    FROM ({dataset_id}.{output_table_id} AS output
          JOIN {dataset_id}.{input_table_id}
          ON {input_table_id}.row_id
          = output.row_id)
    WHERE {output_table_id}.row_id = {input_table_id}.row_id;
                                """)
    job.result()

    return { "success": True }

"""
For a numeric column in the input table, replace null values with the mean non-null value of that
column. 
@param column_name: the name of the column to impute.
"""
def impute_mean(column_name):
    job = bigquery_client.query(f"""
    UPDATE {dataset_id}.{input_table_id}
    SET {column_name} = (SELECT AVG({column_name}) FROM {dataset_id}.{input_table_id})
    WHERE {column_name} IS NULL;
                               """)
    job.result()

    return { "success": True }
"""
For a numeric or categorical column in the input table, replace null values with
the most common (mode) value of that column. 
@param column_name: the name of the column to impute.
"""
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

"""
Checks whether a column in the input table has null values or not.
@param column_name: the name of the column to check
"""
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
First, copy the target column directly to the output table. Do not use the
target column in any other computed columns.

For each feature in the input dataset:
1. determine whether it should be included as input to the machine learning model.
Consider criteria such as relevance, overlap with other features, and effect
size.

2. determine whether the data should be transformed in some way. For example,
   numeric data might need to be normalized or have the logarithm taken, while
   categorical data should be encoded using a numerical encoding.

3. If you have determined that the data should be included, copy it from the
   input dataset to the input_engineered dataset while applying the determined
   transformation (if any).

After these steps have been performed for all features, determine whether any computed
features should also be included. This could include logs, roots or other
functions applied to existing numerical features, as well as features calculated
from multiple other features such as products or sums. Finally, consider whether
numeric data should be binned or bucketed. When deciding whether to create a
computed feature, use criteria of relevance, usefulness and overlap with
previous features. Create the computed features in the input_engineered dataset.

Finally, report all the features chosen and decisions made, as well as the
reasoning behind those decisions.
""",
    tools = [prepare, list_input_columns, list_output_columns, normalize_column, copy_column, 
             logarithm_column, feature_cross,
             feature_difference, impute_mean, impute_mode,
             has_null, target_column]
)

data_agent = Workflow(
    name="data_agent",
    edges=[
        ("START", feature_engineer)
    ]
)

## take target column as input
## report success or failure
## etc
