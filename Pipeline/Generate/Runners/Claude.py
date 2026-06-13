import base64
from anthropic import Anthropic


def _pdf_block(pdf_path: str) -> dict:
    with open(pdf_path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}


def _build_content(message, pdf_path: str | None, is_first: bool):
    if pdf_path and is_first:
        text = message if isinstance(message, str) else None
        blocks = [_pdf_block(pdf_path)]
        if text:
            blocks.append({"type": "text", "text": text})
        elif isinstance(message, list):
            blocks.extend(message)
        return blocks
    return message


def run_chat(messages, api_key, model="claude-sonnet-4-5", temperature=1.0, pdf_path=None):
    client = Anthropic(api_key=api_key)
    full_text = ""
    built = [
        {"role": "user", "content": _build_content(m, pdf_path, i == 0)}
        for i, m in enumerate(messages)
    ]
    with client.messages.stream(
        model=model,
        max_tokens=32000,
        temperature=temperature,
        messages=built,
    ) as stream:
        for text in stream.text_stream:
            full_text += text

    # Check it finished naturally
    if stream.get_final_message().stop_reason == "max_tokens":
        raise RuntimeError(
            "Response hit max_tokens limit — output truncated. "
            "Increase max_tokens further or shorten the prompt."
        )

    return full_text


def checkModels():
    client = Anthropic()
    page = client.models.list()
    #page = page.data[0]
    return page

if __name__ == "__main__":
    print(checkModels())