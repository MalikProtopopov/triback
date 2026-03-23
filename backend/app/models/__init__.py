"""Models package — imports all model modules so Alembic can discover them."""

from app.models.base import Base  # noqa: F401
from app.models.certificate_settings import CertificateSettings  # noqa: F401
from app.models.certificates import Certificate  # noqa: F401
from app.models.cities import City  # noqa: F401
from app.models.content import (  # noqa: F401
    Article,
    ArticleTheme,
    ArticleThemeAssignment,
    ContentBlock,
    OrganizationDocument,
    PageSeo,
)
from app.models.events import (  # noqa: F401
    Event,
    EventGallery,
    EventGalleryPhoto,
    EventRecording,
    EventRegistration,
    EventTariff,
)
from app.models.payment_webhook_inbox import PaymentWebhookInbox  # noqa: F401
from app.models.profiles import (  # noqa: F401
    AuditLog,
    DoctorDocument,
    DoctorProfile,
    DoctorProfileChange,
    DoctorSpecialization,
    ModerationHistory,
    Specialization,
)
from app.models.site import SiteSetting  # noqa: F401
from app.models.subscriptions import (  # noqa: F401
    Payment,
    Plan,
    Receipt,
    Subscription,
)
from app.models.telegram_integration import TelegramIntegration  # noqa: F401
from app.models.users import (  # noqa: F401
    Notification,
    NotificationTemplate,
    Role,
    TelegramBinding,
    User,
    UserRoleAssignment,
)
from app.models.voting import Vote, VotingCandidate, VotingSession  # noqa: F401
