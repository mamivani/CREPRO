from crepro_common import create_app
from crepro_maintenance.api import router

app = create_app("maintenance")
app.include_router(router)
