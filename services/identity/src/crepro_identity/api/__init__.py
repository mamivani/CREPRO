"""HTTP routes for the identity service."""

from crepro_common import build_crud_router
from crepro_identity.models import User
from crepro_identity.repository import users
from crepro_identity.schemas import UserCreate, UserUpdate
from fastapi import APIRouter

router = APIRouter()

router.include_router(
    build_crud_router(
        prefix="/api/v1/users",
        tags=["users"],
        repository=users,
        entity_cls=User,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        not_found_detail="User not found",
    )
)
