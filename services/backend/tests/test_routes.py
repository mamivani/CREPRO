from itertools import combinations

from crepro_backend.main import app as backend_app
from crepro_document.main import app as document_app
from crepro_lease.main import app as lease_app
from crepro_maintenance.main import app as maintenance_app
from crepro_payment.main import app as payment_app
from crepro_property.main import app as property_app
from crepro_reporting.main import app as reporting_app
from crepro_reservation.main import app as reservation_app
from crepro_tenant.main import app as tenant_app
from crepro_utility.main import app as utility_app

DOMAIN_APPS = (
    tenant_app,
    property_app,
    lease_app,
    reservation_app,
    payment_app,
    document_app,
    utility_app,
    maintenance_app,
    reporting_app,
)


def _operations(app) -> set[tuple[str, str]]:
    paths = app.openapi()["paths"]
    return {(method, path) for path, item in paths.items() if path != "/health" for method in item}


def test_every_domain_operation_is_served_by_the_backend() -> None:
    backend_ops = _operations(backend_app)
    for domain_app in DOMAIN_APPS:
        assert _operations(domain_app) <= backend_ops


def test_domain_services_do_not_share_operations() -> None:
    for left, right in combinations(DOMAIN_APPS, 2):
        assert _operations(left).isdisjoint(_operations(right))
