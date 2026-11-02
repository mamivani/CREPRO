from crepro_common import create_app
from crepro_identity.api import router
from crepro_identity.auth import router as auth_router

app = create_app("identity")
app.include_router(router)
app.include_router(auth_router)
