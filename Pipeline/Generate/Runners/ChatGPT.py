import base64
from openai import OpenAI


def _build_content(message, pdf_path: str | None, is_first: bool):
    if pdf_path and is_first:
        with open(pdf_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")
        blocks = [
            {"type": "input_file", "filename": pdf_path.split("/")[-1], "file_data": f"data:application/pdf;base64,{data}"},
        ]
        if isinstance(message, str):
            blocks.append({"type": "input_text", "text": message})
        return blocks
    if isinstance(message, str):
        return message
    return message


def run_chat(messages, api_key, model="gpt-5", temperature=1.0, pdf_path=None):
    client = OpenAI(api_key=api_key, timeout=1200)
    response = client.responses.create(
        model=model,
        input=[
            {"role": "user", "content": _build_content(m, pdf_path, i == 0)}
            for i, m in enumerate(messages)
        ],
        temperature=temperature,
    )
    return response.output_text

def checkModels(api_key):
    client = OpenAI(api_key=api_key,timeout=1200)
    page = client.models.list()
    return page

