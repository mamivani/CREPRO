from crepro_common import create_app
from crepro_reservation.api import router

app = create_app("reservation")
app.include_router(router)
