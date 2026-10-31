from crepro_common import create_app
from crepro_utility.api import router

app = create_app("utility")
app.include_router(router)
