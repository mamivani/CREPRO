from crepro_common import create_app
from crepro_payment.api import router

app = create_app("payment")
app.include_router(router)
