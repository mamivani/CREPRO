from crepro_common import create_app
from crepro_erp_adapter.api import router

app = create_app("erp-adapter")
app.include_router(router)
