from crepro_common import create_app
from crepro_lease.api import router

app = create_app("lease")
app.include_router(router)
