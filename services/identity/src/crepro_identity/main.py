from crepro_common import create_app
from crepro_identity.api import router

app = create_app("identity")
app.include_router(router)
