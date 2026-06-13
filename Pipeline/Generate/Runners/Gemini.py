import google.generativeai as genai
import google.ai.generativelanguage as glm
from google.generativeai.types import GenerationConfig
import os
import time


def _build_parts(messages, pdf_path: str | None) -> list:
    parts = []
    if pdf_path:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        parts.append(glm.Part(inline_data=glm.Blob(mime_type="application/pdf", data=pdf_bytes)))
    parts.append(glm.Part(text="\n\n".join(messages)))
    return parts


def run_chat(messages, api_key, model="gemini-3-flash-preview", retries=2, temperature=1.0, pdf_path=None):
    genai.configure(api_key=api_key)
    contents = _build_parts(messages, pdf_path) if pdf_path else "\n\n".join(messages)
    gemini_model = genai.GenerativeModel(model)

    for attempt in range(retries + 1):
        response = gemini_model.generate_content(
            contents,
            generation_config=GenerationConfig(temperature=temperature),
        )

        # --- SAFE access to response.text ---
        try:
            text = response.text
            if text:
                return text
        except ValueError:
            pass  # no valid text, fall through

        # --- Fallback: inspect structured parts directly ---
        try:
            if response.candidates:
                candidate = response.candidates[0]
                content = candidate.content
                if content and content.parts:
                    texts = [
                        part.text
                        for part in content.parts
                        if hasattr(part, "text") and part.text
                    ]
                    if texts:
                        return "\n".join(texts)
        except Exception:
            pass

        # --- Retry if allowed ---
        if attempt < retries:
            time.sleep(1.5)
            continue

        # --- Final fallback: return diagnostic string ---
        finish_reason = None
        if response.candidates:
            finish_reason = response.candidates[0].finish_reason

        return (
            "[GEMINI_NO_OUTPUT]\n"
            f"finish_reason={finish_reason}"
        )

def checkModels():
    genai.configure()
    for i, m in zip(range(50), genai.list_models()):
        print(f"Name: {m.name} Description: {m.description} support: {m.supported_generation_methods}")


if __name__ == "__main__":
    checkModels()