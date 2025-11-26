from fastapi import APIRouter

from metadata_extractor.app.schemas import WebSearchRequest, WebSearchResponse
from metadata_extractor.app.services.web_search import run_web_search

router = APIRouter(
    prefix="/search",
    tags=["Web Search"],
)


@router.post("/", response_model=WebSearchResponse)
async def web_search(req: WebSearchRequest):
    result = await run_web_search(req)
    return WebSearchResponse(**result)
