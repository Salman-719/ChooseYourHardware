from pydantic import BaseModel

class ExtractionRequest(BaseModel):
    model_type: str = "cnn"
    last_question: str | None = None
    user_input: str | None = None
    cur_state: dict | None = None

class ExtractionResponse(BaseModel):
    metadata: dict


class WebSearchRequest(BaseModel):
    query: str
    context: str | None = None
    model: str | None = None


class WebSearchResponse(BaseModel):
    answer: str
    model_used: str
