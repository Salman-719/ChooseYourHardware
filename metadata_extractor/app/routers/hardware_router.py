from fastapi import APIRouter

from metadata_extractor.app.services.hardware_store import list_hardware
from metadata_extractor.app.services.hardware_crawler import crawl_once

router = APIRouter(
    prefix="/hardware",
    tags=["Hardware"],
)


@router.get("/")
async def get_hardware():
    return {"items": list_hardware()}


@router.post("/crawl")
async def trigger_crawl():
    inserted = await crawl_once()
    return {"inserted": inserted}
