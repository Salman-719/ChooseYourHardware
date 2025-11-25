from fastapi import APIRouter

from metadata_extractor.app.schemas import ExtractionRequest, ExtractionResponse
from metadata_extractor.app.services.extractor import run_metadata_extractor

router = APIRouter(
    prefix="/extractor",
    tags=["Metadata Extractor"]
)

@router.post("/", response_model=ExtractionResponse)
async def extract_metadata(req: ExtractionRequest):
    result = await run_metadata_extractor(req)
    return ExtractionResponse(**result)
