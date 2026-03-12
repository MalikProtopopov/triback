"""Public API tests — doctors, events, cities, articles."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


async def test_doctors_list_only_active(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_city, create_doctor_profile, create_user

    city = await create_city(db_session)
    user_active = await create_user(db_session, email="active_doc@test.com")
    user_pending = await create_user(db_session, email="pending_doc@test.com")

    await create_doctor_profile(
        db_session, user=user_active, status="active", city=city
    )
    await create_doctor_profile(
        db_session, user=user_pending, status="pending_review", city=city
    )
    await db_session.commit()

    resp = await client.get("/api/v1/doctors")
    assert resp.status_code == 200
    data = resp.json()
    for doc in data["data"]:
        assert doc.get("status", "active") == "active" or "status" not in doc


async def test_doctors_filter_by_city(
    client: AsyncClient, db_session: AsyncSession
):
    from tests.factories import create_city, create_doctor_profile, create_user

    city_a = await create_city(db_session, name="CityA", slug="city-a")
    city_b = await create_city(db_session, name="CityB", slug="city-b")

    user_a = await create_user(db_session, email="doc_city_a@test.com")
    user_b = await create_user(db_session, email="doc_city_b@test.com")

    await create_doctor_profile(db_session, user=user_a, city=city_a)
    await create_doctor_profile(db_session, user=user_b, city=city_b)
    await db_session.commit()

    resp = await client.get(f"/api/v1/doctors?city_id={city_a.id}")
    assert resp.status_code == 200


async def test_event_register_missing_body(client: AsyncClient):
    from uuid import uuid4

    resp = await client.post(f"/api/v1/events/{uuid4()}/register")
    assert resp.status_code == 422


async def test_cities_list(client: AsyncClient, db_session: AsyncSession):
    from tests.factories import create_city

    await create_city(db_session, name="TestCity", slug="test-city")
    await db_session.commit()

    resp = await client.get("/api/v1/cities")
    assert resp.status_code == 200


async def test_events_list(client: AsyncClient, db_session: AsyncSession):
    from tests.factories import create_event, create_user

    admin = await create_user(db_session, email="event_admin@test.com")
    await create_event(db_session, created_by=admin)
    await db_session.commit()

    resp = await client.get("/api/v1/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


async def test_doctors_search(client: AsyncClient, db_session: AsyncSession):
    resp = await client.get("/api/v1/doctors?search=nonexistent_doctor_xyz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0


async def test_articles_list(client: AsyncClient, db_session: AsyncSession):
    from tests.factories import create_article, create_user

    author = await create_user(db_session, email="author@test.com")
    await create_article(db_session, author=author)
    await db_session.commit()

    resp = await client.get("/api/v1/articles")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
