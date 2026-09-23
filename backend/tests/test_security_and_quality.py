"""
Comprehensive security and API-quality test suite:
- OWASP security headers injection
- Request tracking via X-Request-ID and X-Process-Time-Ms
- API versioning under /api/v1 and legacy /api backward compatibility
- Strict secret and credential redaction on errors (no leak of DB/Redis URLs)
- Pydantic v2 automatic whitespace stripping and input sanitization
- CORS preflight and exposed headers
- Auth-ready dependency verification
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.error_handling.exceptions import ResourceNotFoundError
from app.main import app
from app.schemas.common import ApiResponse, PaginatedData, PaginationMeta
from app.schemas.current_reading import CurrentReadingApiResponse, CurrentReadingData
from app.schemas.history_reading import HistoryReadingApiResponse, PaginationMetadata
from app.schemas.next_reading import NextReadingApiResponse, NextReadingData
from app.schemas.transformer import TransformerCreate
from app.security.auth import UserContext, get_current_user_optional, require_authenticated_user
from app.utils.sanitizer import mask_connection_string, redact_sensitive_data, sanitize_text

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


# ---------------------------------------------------------------------------
# 1. Security Headers & Request Tracking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Verify all standard OWASP security headers are present on responses."""
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200

    headers = resp.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert headers.get("Content-Security-Policy") == "default-src 'self'"
    assert "geolocation=()" in headers.get("Permissions-Policy", "")


@pytest.mark.asyncio
async def test_request_id_and_process_time_headers(client: AsyncClient):
    """Verify X-Request-ID generation/propagation and X-Process-Time-Ms timing header."""
    # Generated ID
    resp1 = await client.get("/api/v1/health")
    assert "X-Request-ID" in resp1.headers
    assert "X-Process-Time-Ms" in resp1.headers
    assert float(resp1.headers["X-Process-Time-Ms"]) >= 0

    # Custom propagated ID
    custom_id = "custom-trace-uuid-98765"
    resp2 = await client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp2.headers.get("X-Request-ID") == custom_id


# ---------------------------------------------------------------------------
# 2. API Versioning (/api/v1 and legacy /api)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_v1_versioned_routes(client: AsyncClient):
    """All core endpoints are accessible under the official /api/v1 prefix."""
    # Health
    r_health = await client.get("/api/v1/health")
    assert r_health.status_code == 200
    assert r_health.json()["success"] is True

    # Current reading
    with patch("app.routes.reading_routes.CurrentReadingService") as MockCur:
        MockCur.return_value.get_current_reading = AsyncMock(
            return_value=CurrentReadingApiResponse(
                success=True,
                data=CurrentReadingData(
                    transformer_id="T001",
                    voltage=230.0,
                    current=12.5,
                    temperature=65.0,
                    sequence=1,
                ),
            )
        )
        r_cur = await client.get("/api/v1/readings/current")
        assert r_cur.status_code == 200
        assert r_cur.json()["success"] is True

    # Next reading
    with patch("app.routes.reading_routes.NextReadingService") as MockNext:
        MockNext.return_value.get_next_reading = AsyncMock(
            return_value=NextReadingApiResponse(
                success=True,
                data=NextReadingData(
                    transformer_id="T001",
                    voltage=230.0,
                    current=12.5,
                    temperature=65.0,
                    sequence=1,
                    has_next=True,
                    is_end_of_dataset=False,
                    session_id="test-session",
                    total_readings=10,
                ),
            )
        )
        r_next = await client.get("/api/v1/readings/next")
        assert r_next.status_code == 200
        assert r_next.json()["success"] is True

    # History reading
    with patch("app.routes.reading_routes.HistoryReadingService") as MockHist:
        MockHist.return_value.get_reading_history = AsyncMock(
            return_value=HistoryReadingApiResponse(
                success=True,
                data=[],
                pagination=PaginationMetadata(
                    page=1, limit=2, total_items=0, total_pages=0, has_next=False, has_prev=False
                ),
            )
        )
        r_hist = await client.get("/api/v1/readings/history?limit=2")
        assert r_hist.status_code == 200
        assert r_hist.json()["success"] is True

    # Transformers
    with patch("app.routes.transformer_routes.TransformerController") as MockTx:
        MockTx.return_value.list_transformers.return_value = ApiResponse(
            success=True,
            data=PaginatedData(
                items=[], pagination=PaginationMeta(total=0, skip=0, limit=2, has_more=False)
            ).model_dump(),
        )
        r_tx = await client.get("/api/v1/transformers?limit=2")
        assert r_tx.status_code == 200

    # Dataset info
    with patch("app.controllers.dataset_controller.DatasetService") as MockDs:
        MockDs.return_value.get_dataset_info.return_value = MagicMock(
            model_dump=lambda: {"filename": "test.csv", "total_records": 0, "columns": []}
        )
        r_ds = await client.get("/api/v1/dataset/info")
        assert r_ds.status_code == 200

    # Network summary
    with patch("app.routes.network_routes.NetworkController") as MockNet:
        MockNet.return_value.get_summary.return_value = ApiResponse(
            success=True,
            data={"total_transformers": 0, "system_status": "operational"},
        )
        r_net = await client.get("/api/v1/network/summary")
        assert r_net.status_code == 200


@pytest.mark.asyncio
async def test_legacy_api_prefix_backward_compatibility(client: AsyncClient):
    """Existing clients requesting /api continue to function seamlessly."""
    r1 = await client.get("/api/health")
    assert r1.status_code == 200

    with patch("app.routes.reading_routes.CurrentReadingService") as MockCur:
        MockCur.return_value.get_current_reading = AsyncMock(
            return_value=CurrentReadingApiResponse(
                success=True,
                data=CurrentReadingData(
                    transformer_id="T001",
                    voltage=230.0,
                    current=12.5,
                    temperature=65.0,
                    sequence=1,
                ),
            )
        )
        r2 = await client.get("/api/readings/current")
        assert r2.status_code == 200

    with patch("app.routes.reading_routes.NextReadingService") as MockNext:
        MockNext.return_value.get_next_reading = AsyncMock(
            return_value=NextReadingApiResponse(
                success=True,
                data=NextReadingData(
                    transformer_id="T001",
                    voltage=230.0,
                    current=12.5,
                    temperature=65.0,
                    sequence=1,
                    has_next=True,
                    is_end_of_dataset=False,
                    session_id="test-session",
                    total_readings=10,
                ),
            )
        )
        r3 = await client.get("/api/readings/next")
        assert r3.status_code == 200


# ---------------------------------------------------------------------------
# 3. Secret & Credential Redaction / Error Safety
# ---------------------------------------------------------------------------

def test_mask_connection_string_utility():
    """Verify that credentials inside connection strings are masked."""
    raw_pg = "postgresql+asyncpg://postgres:supersecretpass@localhost:5432/transformer_db"
    masked_pg = mask_connection_string(raw_pg)
    assert "supersecretpass" not in masked_pg
    assert "postgres:***@localhost:5432/transformer_db" in masked_pg

    raw_redis = "redis://user:myredispass@redis-server:6379/0"
    masked_redis = mask_connection_string(raw_redis)
    assert "myredispass" not in masked_redis


def test_redact_sensitive_data_dict():
    """Verify recursive redaction of sensitive dictionary fields."""
    payload = {
        "transformer_id": "TR-001",
        "password": "plain_password_123",
        "api_key": "secret_key_abc",
        "nested": {
            "token": "bearer_xyz",
            "safe_val": 42
        }
    }
    redacted = redact_sensitive_data(payload)
    assert redacted["password"] == "***REDACTED***"
    assert redacted["api_key"] == "***REDACTED***"
    assert redacted["nested"]["token"] == "***REDACTED***"
    assert redacted["nested"]["safe_val"] == 42
    assert redacted["transformer_id"] == "TR-001"


@pytest.mark.asyncio
async def test_404_error_contains_request_id_and_no_secrets(client: AsyncClient):
    """404 responses include tracking request ID and do not expose stack traces."""
    with patch("app.routes.transformer_routes.TransformerController") as MockController:
        MockController.return_value.get_transformer.side_effect = ResourceNotFoundError(
            resource="Transformer", identifier="NONEXISTENT_99999"
        )
        resp = await client.get("/api/v1/transformers/NONEXISTENT_99999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["success"] is False
    assert "error" in body
    assert "request_id" in body["error"]
    assert "traceback" not in str(body).lower()


# ---------------------------------------------------------------------------
# 4. Input Sanitization & Pydantic v2 Whitespace Stripping
# ---------------------------------------------------------------------------

def test_pydantic_v2_whitespace_stripping():
    """Pydantic v2 automatically strips whitespace from string fields."""
    item = TransformerCreate(
        id="  TR-STRIP-01  ",
        name="   Substation Omega   ",
        status="operational"
    )
    assert item.id == "TR-STRIP-01"
    assert item.name == "Substation Omega"


def test_sanitize_text_utility():
    """Null bytes and excessive lengths are safely handled."""
    dirty = "  Transformer\x00 Name   "
    clean = sanitize_text(dirty, max_length=20)
    assert clean == "Transformer Name"


# ---------------------------------------------------------------------------
# 5. CORS Configuration & Preflight
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cors_preflight_headers(client: AsyncClient):
    """CORS preflight requests return approved methods and exposed headers."""
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization,X-Request-ID",
    }
    resp = await client.options("/api/v1/transformers", headers=headers)
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


# ---------------------------------------------------------------------------
# 6. Auth-Ready Architecture
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_optional_anonymous():
    """Unauthenticated call returns anonymous user context."""
    user = await get_current_user_optional(token=None, api_key=None)
    assert user.user_id == "anonymous"
    assert user.is_authenticated is False


@pytest.mark.asyncio
async def test_auth_optional_with_credentials():
    """Bearer token or API key populates authenticated user context."""
    from fastapi.security import HTTPAuthorizationCredentials
    token = HTTPAuthorizationCredentials(scheme="Bearer", credentials="test_jwt_token")
    user = await get_current_user_optional(token=token, api_key=None)
    assert user.is_authenticated is True
    assert user.role == "operator"


@pytest.mark.asyncio
async def test_require_authenticated_user_blocks_anonymous():
    """Calling require_authenticated_user with anonymous context raises 401."""
    anon_user = UserContext(user_id="anonymous", is_authenticated=False)
    with pytest.raises(HTTPException) as exc_info:
        await require_authenticated_user(user=anon_user)
    assert exc_info.value.status_code == 401
