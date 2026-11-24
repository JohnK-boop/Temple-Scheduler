import io
import uuid

from google.adk.tools.tool_context import ToolContext
from google.adk.agents.callback_context import CallbackContext

from orchestrator.shared_key import CSV_URI, CSV_NAME, USER_REQUEST
from google.genai.types import Part, Blob
from agents.upload_tools import upload_csv
from agents.model_tools import CLASSIFICATION_MODELS, REGRESSION_MODELS
from typing import List, Dict, Any, Optional

import csv


def tidy_csv_func(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data

    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")  # guess the format
    except csv.Error:
        dialect = csv.excel

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerows(csv.reader(io.StringIO(text), dialect))
    return out.getvalue().encode("utf-8")


# called before every model response
async def save_user_csv(callback_context: CallbackContext):
    content = callback_context.user_content
    if not content or not content.parts:
        return None

    file_part = next(
        (part for part in content.parts if part.inline_data),
        None
    )

    if file_part is None:
        return None

    tidy_csv = Part(inline_data=Blob(
        data=tidy_csv_func(file_part.inline_data.data),
        mime_type="text/csv",
    ))

    file_name = str(uuid.uuid4()) + ".csv"
    await callback_context.save_artifact(file_name, tidy_csv)
    await upload_csv(file_name, callback_context)
    callback_context.state[CSV_NAME] = file_name
    return None


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
        return None
    artifact = await tool_context.load_artifact(tool_context.state[CSV_NAME])
    return artifact


async def read_csv(part: Part) -> csv.reader:
    text = part.inline_data.data.decode("utf-8-sig")
    reader = csv.reader(io.StringIO(text))
    return reader


MAX_ROWS_GUESS = 1000


async def read_csv_get_all_key(tool_context: ToolContext) -> dict[str, Any]:
    result = {"message": "", "column": []}
    part = await get_csv_uploaded(tool_context)
    if part is None:
        result["message"] = "Tell user to upload a CSV file first."
        return result
    reader = await read_csv(part)

    if not reader:
        result["message"] = "Tell the user that the reader was null."
        return result

    count_row = 0
    guess_data = {}

    first_row = next(reader, None)
    if first_row is None:
        result["message"] = "CSV file is empty."
        return result

    while True:
        if count_row >= MAX_ROWS_GUESS:
            break
        iter_row = next(reader, None)
        if iter_row is None:
            if count_row == 0:
                result["message"] = "CSV file is empty."
                return result
            else:
                break
        count_row += 1
        for k, field in enumerate(iter_row):
            value = field
            if str(value).strip() == "":
                continue
            type_name = guess_type(value)
            if k not in guess_data:
                guess_data[k] = {type_name: 1}
            else:
                if type_name not in guess_data[k]:
                    guess_data[k][type_name] = 1
                else:
                    guess_data[k][type_name] += 1

    for g in guess_data.items():
        index, type_counts = g
        most_common_type = max(type_counts, key=type_counts.get)
        result["column"].append({"key": first_row[index], "type": most_common_type})

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
    return {"message": f"Target column '{target_column}' selected.", "target_column": target_column}


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
