import io
import uuid

from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext

from orchestrator.shared_key import CSV_URI, CSV_NAME, USER_REQUEST
from google.genai.types import Part
from agents.upload_tools import upload_csv
from agents.model_tools import CLASSIFICATION_MODELS, REGRESSION_MODELS
from typing import List, Dict, Any, Optional

import csv


async def save_user_csv(callback_context: CallbackContext):
    content = callback_context.user_content
    if not content or not content.parts:
        return None

    file_part = next(
        (part for part in content.parts if part.inline_data and part.part_metadata.get("file_type") == "csv"),
        None
    )

    if file_part is None:
        return None

    file_name = str(uuid.uuid4()) + ".csv"
    await callback_context.save_artifact(file_name, file_part)
    await upload_csv(file_name, callback_context)
    callback_context.state[CSV_NAME] = file_name



def guess_type(value: str) -> str:
    if value == "":
        return "str"
    try:
        int(value)
        return "int"
    except ValueError:
        pass

    try:
        float(value)
        return "float"
    except ValueError:
        pass

    if value.lower() in ["true", "false"]:
        return "bool"

    return "str"


async def get_csv_uploaded(tool_context: ToolContext) -> Optional[Part]:
    if CSV_NAME not in tool_context.state:
        return False
    artifact = await tool_context.load_artifact(tool_context.state[CSV_NAME])
    return artifact


async def read_csv(part: Part) -> csv.reader:
    text = part.inline_data.data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    return reader


async def read_csv_get_all_key(tool_context: ToolContext) -> dict[str, Any]:
    result = {"message": "", "column": []}
    part = await get_csv_uploaded(tool_context)
    if part is None:
        result["message"] = "Tell user to upload a CSV file first."
        return result
    reader = await read_csv(part)

    first_row = next(reader, None)
    if first_row is None:
        result["message"] = "CSV file is empty."
        return result

    for k, field in enumerate(first_row.keys()):
        value = first_row[field]
        type_name = guess_type(value)
        result["column"].append({"key": field, "type": type_name})
    return result


async def select_target(tool_context: ToolContext, target_column: str) -> dict[str, Any]:
    result = {"message": "", "target_column": None}
    part = await get_csv_uploaded(tool_context)
    if part is None:
        result["message"] = "Tell user to upload a CSV file first."
        return result

    reader = await read_csv(part)

    first_row = next(reader, None)
    if first_row is None:
        result["message"] = "CSV file is empty."
        return result

    if target_column not in first_row:
        result["message"] = f"Column '{target_column}' not found in CSV."
        return result

    tool_context.state["target_column"] = target_column


async def select_model(tool_context: ToolContext, model_type: str) -> dict[str, Any]:
    result = {"message": "", "model_type": None}
    if not model_type:
        result["message"] = "Model type is empty."
        return result

    if model_type not in CLASSIFICATION_MODELS and model_type not in REGRESSION_MODELS:
        result["message"] = f"Unknown model type '{model_type}'. Use list_model_options to see available models."
        return result

    tool_context.state["model_type"] = model_type
    result["model_type"] = model_type
    return result