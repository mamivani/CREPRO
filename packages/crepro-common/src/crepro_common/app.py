from fastapi import FastAPI

from crepro_common.telemetry import instrument_app


def create_app(service_name: str) -> FastAPI:
    app = FastAPI(title=f"CREPRO {service_name}", version="0.1.0")

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"service": service_name, "status": "ok"}

    instrument_app(app, service_name)
    return app
