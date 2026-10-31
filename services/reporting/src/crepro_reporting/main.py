from crepro_common import create_app
from crepro_reporting.api import router

app = create_app("reporting")
app.include_router(router)
