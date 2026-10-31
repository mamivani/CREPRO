from crepro_common import create_app
from crepro_document.api import router

app = create_app("document")
app.include_router(router)
