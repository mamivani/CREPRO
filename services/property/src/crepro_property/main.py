from crepro_common import create_app
from crepro_property.api import router

app = create_app("property")
app.include_router(router)
