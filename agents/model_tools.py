# Model agent tools - John

import re
from google.cloud import bigquery
from orchestrator.shared_key import PROJECT_ID, TRAINING_TABLE

PROJECT = PROJECT_ID
DATASET = "agent_data"

client = bigquery.Client(project=PROJECT)

CLASSIFICATION_MODELS = ["LOGISTIC_REG", "BOOSTED_TREE_CLASSIFIER"]
REGRESSION_MODELS = ["LINEAR_REG", "BOOSTED_TREE_REGRESSOR"]


# make sure names are safe to put in sql
def check_name(name):
    if re.fullmatch(r"[A-Za-z0-9_.]+", name) == None:
        raise ValueError("Invalid name: " + name)
    return name

def run_query(sql):
    job_config = bigquery.QueryJobConfig(use_query_cache=False)
    query_job = client.query(sql, job_config=job_config)
    rows = query_job.result()

    results = []
    for row in rows:
        results.append(dict(row.items()))
    return results

def list_model_options(task_type: str = ""):
    """Lists the model types that can be trained. task_type is "classification", "regression", or empty for both."""
    if task_type == "classification":
        return {"ok": True, "classification": CLASSIFICATION_MODELS}
    elif task_type == "regression":
        return {"ok": True, "regression": REGRESSION_MODELS}
    else:
        return {"ok": True, "classification": CLASSIFICATION_MODELS, "regression": REGRESSION_MODELS}

def train_model(target: str, model_type: str, model_name: str = ""):
    """Trains a BigQuery ML model on a table (like "agent_data.student_por") to predict the target column.
    Leave model_name blank to get an automatic versioned name."""
    try:
        model_type = model_type.upper()

        if model_type not in CLASSIFICATION_MODELS and model_type not in REGRESSION_MODELS:
            return {"ok": False, "error": "Unknown model type " + model_type, "hint": "use list_model_options"}

        if model_name == "":
            model_name = make_model_name("agent", model_type)

        check_name(target)
        check_name(model_name)

        sql = f"""
        CREATE OR REPLACE MODEL `{PROJECT}.{DATASET}.{model_name}`
        OPTIONS(
          model_type = '{model_type}',
          input_label_cols = ['{target}'],
          enable_global_explain = TRUE
        ) AS
        SELECT * EXCEPT (row_id)
        FROM `{PROJECT}.{TRAINING_TABLE}`
        """

        run_query(sql)

        return {
            "ok": True,
            "model_name": model_name,
            "model_type": model_type,
            "target": target,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def evaluate_model(model_name: str):
    """Gets the evaluation scores for a trained model."""
    try:
        check_name(model_name)

        # no data given = uses the test data bigquery held back
        sql = f"SELECT * FROM ML.EVALUATE(MODEL `{PROJECT}.{DATASET}.{model_name}`)"
        rows = run_query(sql)

        metrics = {}
        for key in rows[0]:
            value = rows[0][key]
            if type(value) == float:
                value = round(value, 3)
            metrics[key] = value

        return {"ok": True, "model_name": model_name, "metrics": metrics}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def explain_model(model_name: str, top_n: int = 10):
    """Gets the most important features for a trained model."""
    try:
        check_name(model_name)

        sql = f"""
        SELECT feature, attribution
        FROM ML.GLOBAL_EXPLAIN(MODEL `{PROJECT}.{DATASET}.{model_name}`)
        ORDER BY attribution DESC
        LIMIT {int(top_n)}
        """
        rows = run_query(sql)

        features = []
        for row in rows:
            features.append({
                "feature": row["feature"],
                "attribution": round(row["attribution"], 3),
            })

        return {"ok": True, "model_name": model_name, "top_features": features}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def predict(model_name: str, limit: int = 10):
    """Uses a trained model to make predictions on a table."""
    try:
        check_name(model_name)

        sql = f"""
        SELECT *
        FROM ML.PREDICT(MODEL `{PROJECT}.{DATASET}.{model_name}`,
          (SELECT * FROM `{PROJECT}.{TRAINING_TABLE}`))
        LIMIT {int(limit)}
        """
        rows = run_query(sql)

        # only keep the prediction columns
        predictions = []
        for row in rows:
            pred = {}
            for key in row:
                if key.startswith("predicted_"):
                    pred[key] = row[key]
            predictions.append(pred)

        return {"ok": True, "model_name": model_name, "predictions": predictions}
    except Exception as e:
        return {"ok": False, "error": str(e)}

def make_model_name(table: str, model_type: str) -> str:
    """Makes the next unused model name: <table>_<model_type>_v<N>."""
    if model_type not in CLASSIFICATION_MODELS and model_type not in REGRESSION_MODELS:
        raise ValueError("Unknown model type " + model_type + ". Use list_model_options.")

    name = (table.split(".")[-1] + "_" + model_type).lower()

    nums = []
    for m in client.list_models(f"{PROJECT}.{DATASET}"):
        if m.model_id.startswith(name + "_v"):
            version = m.model_id.rsplit("_v", 1)[1]
            if version.isdigit():
                nums.append(int(version))

    return f"{name}_v{max(nums, default=0) + 1}"