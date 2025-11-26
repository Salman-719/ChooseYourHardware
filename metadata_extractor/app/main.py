from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.extractor_router import router as extractor_router
from .routers.web_search_router import router as web_search_router

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

@app.get("/")
def root():
    return {"msg": "Metadata Extractor API running"}
