"""SQLAlchemy models for Markee."""
from app.models.database import Base
from app.models.user import User
from app.models.team import Team, TeamMember
from app.models.subscription import Subscription
from app.models.trademark import Trademark
from app.models.lifecycle import LifecycleEvent, Deadline
from app.models.watchlist import Watchlist, WatchlistItem
from app.models.alert import Alert, Notification
from app.models.portfolio import ClientPortfolio, ProspectionOpportunity
from app.models.source import Source, SourceRun
from app.models.holder import Holder, TrademarkHolder
from app.models.representative import Representative, TrademarkRepresentative
from app.models.trademark_version import TrademarkVersion
from app.models.nice_class import NiceClass
from app.models.goods_services import GoodsServices
from app.models.document import Document
from app.models.review_queue import ReviewQueueItem
from app.models.raw_response import RawApiResponse
from app.models.email_verification import (
    EmailDeliveryRecord,
    EmailVerificationToken,
)
from app.models.schemas import (
    ALL_SCHEMAS,
    SCHEMA_APP,
    SCHEMA_CORE,
    SCHEMA_EVENTS,
    SCHEMA_RAW,
    SQLITE_SCHEMA_TRANSLATE_MAP,
)

__all__ = [
    "Base",
    "User",
    "Team",
    "TeamMember",
    "Subscription",
    "Trademark",
    "LifecycleEvent",
    "Deadline",
    "Watchlist",
    "WatchlistItem",
    "Alert",
    "Notification",
    "ClientPortfolio",
    "ProspectionOpportunity",
    "Source",
    "SourceRun",
    "Holder",
    "TrademarkHolder",
    "Representative",
    "TrademarkRepresentative",
    "TrademarkVersion",
    "NiceClass",
    "GoodsServices",
    "Document",
    "ReviewQueueItem",
    "RawApiResponse",
    "EmailDeliveryRecord",
    "EmailVerificationToken",
    "ALL_SCHEMAS",
    "SCHEMA_APP",
    "SCHEMA_CORE",
    "SCHEMA_EVENTS",
    "SCHEMA_RAW",
    "SQLITE_SCHEMA_TRANSLATE_MAP",
]
