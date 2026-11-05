from crepro_common import create_app
from crepro_property.api import router
from crepro_property.repository import outbox

app = create_app("property", outbox=outbox)
app.include_router(router)
