from openai import OpenAI

from metadata_extractor.app.config import (
    OPENAI_API_KEY,
    OPENAI_WEB_MODEL,
    WEB_SEARCH_SYSTEM_PROMPT,
)
from metadata_extractor.app.schemas import WebSearchRequest

client = OpenAI(api_key=OPENAI_API_KEY)


async def run_web_search(search_request: WebSearchRequest):
    system_content = WEB_SEARCH_SYSTEM_PROMPT
    if search_request.context:
        system_content = f"{system_content}\n\nExtra context: {search_request.context}"

    model = search_request.model or OPENAI_WEB_MODEL

    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": search_request.query},
        ],
        tools=[{"type": "web_search"}],
    )

    return {
        "answer": response.output_text,
        "model_used": model,
    }
