"""Entry point for the ERP stub service (uvicorn crepro_erp_stub.main:app)."""

from crepro_erp_stub.api import router
from fastapi import FastAPI

app = FastAPI(title="CREPRO ERP Stub", version="0.1.0")
app.include_router(router)
