from openai import OpenAI, max_retries
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from collections.abc import Iterator

T = TypeVar("T", bound=BaseModel)

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

def call_json(
    system_prompt: str,
    user_prompt: str,
    schema: Type[T],
    model: str,
    max_retries: int = 2, 
) -> T:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
        ]
    
    last_error: ValidationError | None = None

    for _ in range(max_retries + 1):
        response = get_client().chat.completions.create(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        try:
            return schema.model_validate_json(raw)
        except ValidationError as err:
            last_error = err
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Your previous response does not match the required "
                        f"schema. Validation error:\n{err}\n"
                        "Respond again with ONLY the corrected JSON object."
                    )
                }
                )
    raise RuntimeError(
    f"No valid JSON after {max_retries + 1} attempts. Last error:\n{last_error}")

def call_stream(system_prompt: str, user_prompt: str, model: str) -> Iterator[str]:
    stream = get_client().chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        stream=True
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta

