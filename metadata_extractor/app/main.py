from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.extractor_router import router as extractor_router
from .routers.web_search_router import router as web_search_router
from .routers.hardware_router import router as hardware_router
from metadata_extractor.app.services.hardware_store import init_db
from metadata_extractor.app.services.hardware_crawler import start_periodic_crawl, stop_periodic_crawl

app = FastAPI(
    title="Metadata Extractor API",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # allow all domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extractor_router)
app.include_router(web_search_router)
app.include_router(hardware_router)


@app.on_event("startup")
async def startup_event():
    init_db()
    start_periodic_crawl()


@app.on_event("shutdown")
async def shutdown_event():
    await stop_periodic_crawl()


@app.get("/")
def root():
    return {"msg": "Metadata Extractor API running"}
