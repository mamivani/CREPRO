from crepro_common import create_app
from crepro_tenant.api import router

app = create_app("tenant")
app.include_router(router)
