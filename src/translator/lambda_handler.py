import json
from pathlib import Path

from translator.pipeline import translate_file


def handler(event, context):
    """AWS Lambda-style entrypoint using local paths for this take-home test."""
    if event.get("storage", "local") != "local":
        raise NotImplementedError("Only local storage is implemented for the take-home test")

    input_path = Path(event["input_path"])
    output_dir = Path(event.get("output_dir", "output"))
    translated_path = translate_file(input_path, output_dir)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "translated_file": str(translated_path),
                "source_file": str(input_path),
            }
        ),
    }
