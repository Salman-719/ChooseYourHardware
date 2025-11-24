from fastapi import APIRouter
from app.schemas import ExtractionRequest, ExtractionResponse
from app.services.extractor import run_metadata_extractor

router = APIRouter(
    prefix="/extractor",
    tags=["Metadata Extractor"]
)

@router.post("/", response_model=ExtractionResponse)
async def extract_metadata(req: ExtractionRequest):
    result = await run_metadata_extractor(req)
    return ExtractionResponse(**result)
