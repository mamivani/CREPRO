from fastapi import FastAPI


def create_app(service_name: str) -> FastAPI:
    app = FastAPI(title=f"CREPRO {service_name}", version="0.1.0")

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"service": service_name, "status": "ok"}

    return app
