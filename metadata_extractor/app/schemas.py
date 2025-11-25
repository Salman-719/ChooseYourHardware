from typing import Optional

from pydantic import BaseModel

class ExtractionRequest(BaseModel):
    model_type: str = "cnn"
    last_question: Optional[str] = None
    user_input: Optional[str] = None
    cur_state: Optional[dict] = None

class ExtractionResponse(BaseModel):
    metadata: dict


class WebSearchRequest(BaseModel):
    query: str
    context: Optional[str] = None
    model: Optional[str] = None


class WebSearchResponse(BaseModel):
    answer: str
    model_used: str
