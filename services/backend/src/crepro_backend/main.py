from crepro_common import create_app
from crepro_document.api import router as document_router
from crepro_lease.api import router as lease_router
from crepro_maintenance.api import router as maintenance_router
from crepro_payment.api import router as payment_router
from crepro_property.api import router as property_router
from crepro_property.repository import outbox
from crepro_reporting.api import router as reporting_router
from crepro_reservation.api import router as reservation_router
from crepro_tenant.api import router as tenant_router
from crepro_utility.api import router as utility_router

app = create_app("backend", outbox=outbox)

for domain_router in (
    tenant_router,
    property_router,
    lease_router,
    reservation_router,
    payment_router,
    document_router,
    utility_router,
    maintenance_router,
    reporting_router,
):
    app.include_router(domain_router)
