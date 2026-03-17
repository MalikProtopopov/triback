"""Factory-boy factories for test data creation.

These are plain async helpers (not SQLAlchemyModelFactory) since we use
async sessions with manual flush. Call them with the test db_session.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.security import hash_password
from app.models.cities import City
from app.models.content import Article, OrganizationDocument, PageSeo
from app.models.events import Event, EventGallery, EventRegistration, EventTariff
from app.models.profiles import DoctorProfile, DoctorProfileChange
from app.models.subscriptions import Payment, Plan, Receipt, Subscription
from app.models.users import Role, User, UserRoleAssignment

DEFAULT_PASSWORD = "TestPass123!"
DEFAULT_PASSWORD_HASH = hash_password(DEFAULT_PASSWORD)

_seq = 0


def _next_seq() -> int:
    global _seq
    _seq += 1
    return _seq


async def create_user(
    db,
    *,
    email: str | None = None,
    password_hash: str | None = None,
    is_active: bool = True,
    email_verified_at: datetime | None = None,
) -> User:
    user = User(
        email=email or f"user_{uuid4().hex[:8]}@test.com",
        password_hash=password_hash or DEFAULT_PASSWORD_HASH,
        is_active=is_active,
        email_verified_at=email_verified_at,
    )
    db.add(user)
    await db.flush()
    return user


async def create_role(db, *, name: str, title: str | None = None) -> Role:
    role = Role(name=name, title=title or name.capitalize())
    db.add(role)
    await db.flush()
    return role


async def assign_role(db, user: User, role: Role) -> UserRoleAssignment:
    assignment = UserRoleAssignment(user_id=user.id, role_id=role.id)
    db.add(assignment)
    await db.flush()
    return assignment


async def create_city(
    db, *, name: str | None = None, slug: str | None = None
) -> City:
    n = _next_seq()
    city = City(
        name=name or f"City {n}",
        slug=slug or f"city-{n}",
        is_active=True,
    )
    db.add(city)
    await db.flush()
    return city


async def create_doctor_profile(
    db,
    *,
    user: User | None = None,
    status: str = "active",
    city: City | None = None,
    has_medical_diploma: bool = True,
) -> DoctorProfile:
    if user is None:
        user = await create_user(db)
    n = _next_seq()
    profile = DoctorProfile(
        user_id=user.id,
        first_name=f"Fname{n}",
        last_name=f"Lname{n}",
        phone=f"+7900{n:07d}",
        status=status,
        has_medical_diploma=has_medical_diploma,
        city_id=city.id if city else None,
        slug=f"doctor-{n}",
    )
    db.add(profile)
    await db.flush()
    return profile


async def create_plan(
    db,
    *,
    code: str | None = None,
    name: str | None = None,
    price: float = 5000.0,
    duration_months: int = 12,
) -> Plan:
    n = _next_seq()
    plan = Plan(
        code=code or f"plan_{n}",
        name=name or f"Plan {n}",
        price=price,
        duration_months=duration_months,
        is_active=True,
    )
    db.add(plan)
    await db.flush()
    return plan


async def create_subscription(
    db,
    *,
    user: User,
    plan: Plan,
    status: str = "active",
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
) -> Subscription:
    now = datetime.now(UTC)
    sub = Subscription(
        user_id=user.id,
        plan_id=plan.id,
        status=status,
        starts_at=starts_at or now,
        ends_at=ends_at or (now + timedelta(days=365)),
    )
    db.add(sub)
    await db.flush()
    return sub


async def create_payment(
    db,
    *,
    user: User,
    amount: float = 5000.0,
    product_type: str = "subscription",
    status: str = "pending",
    subscription: Subscription | None = None,
    external_payment_id: str | None = None,
) -> Payment:
    payment = Payment(
        user_id=user.id,
        amount=amount,
        product_type=product_type,
        payment_provider="yookassa",
        status=status,
        subscription_id=subscription.id if subscription else None,
        external_payment_id=external_payment_id,
    )
    db.add(payment)
    await db.flush()
    return payment


async def create_event(
    db,
    *,
    created_by: User,
    title: str | None = None,
    slug: str | None = None,
    status: str = "upcoming",
    event_date: datetime | None = None,
) -> Event:
    n = _next_seq()
    event = Event(
        title=title or f"Event {n}",
        slug=slug or f"event-{n}",
        status=status,
        event_date=event_date or (datetime.now(UTC) + timedelta(days=30)),
        created_by=created_by.id,
    )
    db.add(event)
    await db.flush()
    return event


async def create_article(
    db,
    *,
    author: User,
    title: str | None = None,
    slug: str | None = None,
    status: str = "published",
) -> Article:
    n = _next_seq()
    article = Article(
        title=title or f"Article {n}",
        slug=slug or f"article-{n}",
        content=f"Content for article {n}",
        status=status,
        author_id=author.id,
        published_at=datetime.now(UTC) if status == "published" else None,
    )
    db.add(article)
    await db.flush()
    return article


async def create_event_tariff(
    db,
    *,
    event: Event,
    name: str | None = None,
    price: float = 1000.0,
    member_price: float = 500.0,
    seats_limit: int | None = None,
) -> EventTariff:
    n = _next_seq()
    tariff = EventTariff(
        event_id=event.id,
        name=name or f"Tariff {n}",
        price=price,
        member_price=member_price,
        seats_limit=seats_limit,
        is_active=True,
    )
    db.add(tariff)
    await db.flush()
    return tariff


async def create_event_registration(
    db,
    *,
    user: User,
    event: Event,
    tariff: EventTariff,
    status: str = "confirmed",
    applied_price: float = 1000.0,
    is_member_price: bool = False,
) -> EventRegistration:
    reg = EventRegistration(
        user_id=user.id,
        event_id=event.id,
        event_tariff_id=tariff.id,
        applied_price=applied_price,
        is_member_price=is_member_price,
        status=status,
    )
    db.add(reg)
    await db.flush()
    return reg


async def create_event_gallery(
    db,
    *,
    event: Event,
    title: str | None = None,
    access_level: str = "public",
) -> EventGallery:
    n = _next_seq()
    gallery = EventGallery(
        event_id=event.id,
        title=title or f"Gallery {n}",
        access_level=access_level,
    )
    db.add(gallery)
    await db.flush()
    return gallery


async def create_page_seo(
    db,
    *,
    slug: str | None = None,
    title: str | None = None,
) -> PageSeo:
    n = _next_seq()
    page = PageSeo(
        slug=slug or f"page-{n}",
        title=title or f"Page {n}",
    )
    db.add(page)
    await db.flush()
    return page


async def create_org_document(
    db,
    *,
    title: str | None = None,
    slug: str | None = None,
) -> OrganizationDocument:
    n = _next_seq()
    doc = OrganizationDocument(
        title=title or f"Document {n}",
        slug=slug or f"doc-{n}",
        content="Test document content",
        is_active=True,
    )
    db.add(doc)
    await db.flush()
    return doc


async def create_receipt(
    db,
    *,
    payment: Payment,
    receipt_type: str = "payment",
    status: str = "succeeded",
    receipt_url: str | None = "https://receipt.example.com/123",
) -> Receipt:
    receipt = Receipt(
        payment_id=payment.id,
        receipt_type=receipt_type,
        amount=payment.amount,
        status=status,
        receipt_url=receipt_url,
    )
    db.add(receipt)
    await db.flush()
    return receipt


async def create_profile_change(
    db, *, profile: DoctorProfile, changes: dict | None = None
) -> DoctorProfileChange:
    change = DoctorProfileChange(
        doctor_profile_id=profile.id,
        changes=changes or {"bio": "Updated bio"},
        changed_fields=list((changes or {"bio": "Updated bio"}).keys()),
        status="pending",
    )
    db.add(change)
    await db.flush()
    return change
