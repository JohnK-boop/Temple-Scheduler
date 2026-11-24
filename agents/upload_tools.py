import os
from google.adk.tools import ToolContext
from google.cloud import storage
from orchestrator.shared_key import CSV_URI, CSV_NAME, GCS_BUCKET

BUCKET_NAME = GCS_BUCKET
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def error(msg: str) -> dict:
    return {
        "ok": False,
        "error": msg
    }

async def upload_csv(file_name: str, tool_context: ToolContext) -> dict:
    """
    Uploads CSV file to Cloud Storage and returns its name and uri
    Args:
        file_name: the exact name of the uploaded file, including file extensions
    
    Returns:
        {"ok": True, "csv_name", "csv_uri"} on success,
        or {"ok": False, "error"} if the file is missing or not a CSV.
    """
    name, ext = os.path.splitext(file_name)
    if (ext.lower() != ".csv"):
        return error("Only .csv files are accepted")
    
    try:
        part = await tool_context.load_artifact(file_name) #Wait until the file is loaded from chat
        if (part is None):
            return error(f"File not found: {file_name}")

        #Upload to Bucket
        path = f"uploads/{file_name}"
        uri = f"gs://{BUCKET_NAME}/{path}"
        bucket.blob(path).upload_from_string(part.inline_data.data, content_type="text/csv")
    except Exception as e:
        return error(str(e))
    
    tool_context.state[CSV_URI] = uri
    tool_context.state[CSV_NAME] = name.replace("-", "_")
    return {
        "ok": True,
        "csv_name": name.replace("-", "_"),
        "csv_uri": uri
    }
