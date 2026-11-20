# Step 3.02 — Serializers, ViewSets and Swagger

| | |
|---|---|
| **Goal** | The core entities are reachable over the API — locations with full CRUD, ride modes and LGUs read-only, driver-scoped vehicles and accreditations — and `/api/docs/` renders the whole surface, auth endpoints included |
| **Day / Time** | Day 16 (Sat 21 Nov) · ~3 hours |
| **Prerequisites** | [Step 3.01](01-jwt-auth-and-otp.md) — tokens exist, so every endpoint here can demand a bearer |
| **Traces to** | Milestone M3's "Swagger UI renders" criterion · `mock1_home.png` (locations are the booking screen's data source) · `mock4_driver.png` (vehicle + accreditation) · D-64 (booking_fee surfaced read-only) |
| **Produces** | `apps/rides/{serializers,views,urls}.py`, `apps/accounts/permissions.py`, extensions to `apps/accounts/{serializers,views,urls}.py`, schema routes in `config/urls.py`, `tests/test_core_api.py` |

---

## What this step is really doing

Three object-orientation ideas land in real code here, which is why the step is
graded content and not plumbing:

| Pattern | Where | What it buys |
|---|---|---|
| **ViewSet as repository** | `LocationViewSet` etc. | CRUD over one model is *already* the domain logic — `ModelViewSet` over a manager is thin by construction |
| **Permission as strategy** | `IsDriver` | "only drivers" is a composable object, not an `if` inside each view |
| **Serializer as boundary** | `LocationSerializer` | input shape is validated at the edge; the model stays clean |

The one hard rule still applies: `ModelViewSet` is legitimate *here* because a
write to one table **is** the whole operation. The moment a write spans tables —
booking writes `RIDE` + `RIDE_LEG` — it moves into a service (Steps 3.05+), and
the viewset shrinks to a wrapper.

Swagger is not decoration. It is **the M3 proof surface**: every later step is
verified by walking `/api/docs/` with a token, and the frontend has a machine-readable
contract to build against in Phase 4.

Two facts about the Phase 2 code shape everything below:

- **`REST_FRAMEWORK` paginates globally** (`PAGE_SIZE = 20`), so every *list*
  response is `{"count": …, "results": […]}`. Tests and curl checks must read
  `results`; create/retrieve responses are plain objects.
- **`RideModeLookup.mode` and `Accreditation.lgu` are natural-key FKs**
  (`to_field="mode_code"` / `"lgu_code"`), so serializers expose them with
  `SlugRelatedField` — a driver registers a vehicle with `"mode": "TRICYCLE"`,
  never with a UUID.

---

## Do this

### 0. Before you start (~5 min)

```powershell
Set-Location "C:\Users\MCC IT Admin\Downloads\MIT\CCS670-Object-Orented Software Development\Project\ride-hailingSystem"
docker compose up -d
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest -q --no-cov          # 139 passed — 122 from Phase 2 + 17 from Step 3.01
```

Commit the Step 3.01 work first if it is still uncommitted, so this step's
commit carries only Step 3.02.

> **Note on linting**: `ruff` is already present (installed via `dev.txt` since
> Phase 1). Run `..\.venv\Scripts\ruff.exe check apps tests` any time to verify
> the gate.

---

### 1. Wire the schema URLs (~15 min)

`drf-spectacular` is installed and `SPECTACULAR_SETTINGS` already exists in
`settings.py` (Step 1.06). Add one key — split request/response components, so
a field can be write-only in requests without disappearing from responses:

```python
SPECTACULAR_SETTINGS = {
    # … every existing key stays …
    "COMPONENT_SPLIT_REQUEST": True,
}
```

Then replace `backend/config/urls.py`:

```python
"""URL configuration for Sakay.ph.

Phase 3 mounts each app's API under /api/ as its step lands. Step 3.01 wired
accounts (register, login, refresh, me, OTP); Step 3.02 adds the schema and
the ride-domain read/write endpoints.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.rides.urls")),
]
```

The `url_name="schema"` on the Swagger view must match the schema route's
`name=` — that is the entire wiring contract between the two lines.

Check it renders before writing any serializer:

```powershell
python manage.py runserver
# browser → http://127.0.0.1:8000/api/docs/   — a (near-empty) Swagger page
# browser → http://127.0.0.1:8000/api/schema/ — the raw OpenAPI JSON
```

---

### 2. Document the Step 3.01 auth views (~15 min)

Plain `APIView`s give spectacular nothing to infer from, so the auth endpoints
would appear as undocumented blobs in Swagger. Add decorators — the request
serializers already exist; this is four small edits in
`apps/accounts/views.py`:

```python
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        …
```

| View | Decorator |
|---|---|
| `RegisterView.post` | `@extend_schema(request=RegisterSerializer, responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})` |
| `MeView.get` | `@extend_schema(responses=OpenApiTypes.OBJECT)` |
| `OtpRequestView.post` | `@extend_schema(request=OtpRequestSerializer, responses={200: OpenApiTypes.OBJECT, 429: OpenApiTypes.OBJECT})` |
| `OtpVerifyView.post` | `@extend_schema(request=OtpVerifySerializer, responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT})` |
| `LoginView` | none — `serializer_class` is already set, so spectacular builds the request body from it |

---

### 3. The permission class (~10 min)

Create `backend/apps/accounts/permissions.py`:

```python
"""DRF permission classes — strategy objects the views compose in."""

from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    """Allows access only to authenticated users holding a DRIVER role."""

    message = "Only drivers may do this."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_driver
        )
```

`is_driver` is the property Phase 2 put on `User` — the permission reads the
domain instead of re-deriving the role, which is the whole point of having it.

---

### 4. The ride-domain serializers (~25 min)

Create `backend/apps/rides/serializers.py`:

```python
"""Ride-domain API serializers.

`Location` is the booking screens' write path; the lookups are read-only
because their rows are reference data owned by seed_lookups and the admin.
"""

from decimal import Decimal

from rest_framework import serializers

from apps.accounts.models import LGUUnit
from apps.rides.models import Location, RideModeLookup


class LocationSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-90"), max_value=Decimal("90"),
    )
    longitude = serializers.DecimalField(
        max_digits=9, decimal_places=6,
        min_value=Decimal("-180"), max_value=Decimal("180"),
    )

    class Meta:
        model = Location
        fields = ["id", "street", "barangay", "city", "province",
                  "landmark", "latitude", "longitude"]
        read_only_fields = ["id"]


class RideModeSerializer(serializers.ModelSerializer):
    """Read-only exposure of the Lahat ng Sakyan rate card.

    booking_fee is D-64's ₱3.00 flat, read from the seeded row — rates are
    data (D-62), never code, and never edited through the API.
    """

    class Meta:
        model = RideModeLookup
        fields = ["mode_code", "mode_name", "base_fare", "per_km_rate",
                  "seat_capacity", "is_shared", "booking_fee"]


class LGUUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = LGUUnit
        fields = ["lgu_code", "lgu_name", "province", "region", "contact_no"]
```

**Key fix from review**: `LGUUnit` is imported from `apps.accounts.models`
(not `apps.rides.models`).

Note the coordinate bounds: declared as field validators rather than an
imperative `validate()` — declarative checks read as data, fail with a clean
field-level 400, and are what `mock1`'s map needs to trust.

---

### 5. The ride-domain viewsets (~20 min)

Replace `backend/apps/rides/views.py`:

```python
"""Ride-domain endpoints — thin CRUD over the Phase 2 models."""

from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.accounts.models import LGUUnit
from apps.rides.models import Location, RideModeLookup
from apps.rides.serializers import (
    LGUUnitSerializer, LocationSerializer, RideModeSerializer,
)


class ProtectedDestroyMixin:
    """Turns the models' PROTECT foreign keys into a clean 409.

    LOCATION is referenced by RIDE with on_delete=PROTECT. Without this
    mixin, deleting a referenced location surfaces Django's raw 500; with
    it, the client learns the row is load-bearing.
    """

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response(
                {"detail": "This row is referenced by other records and cannot be deleted."},
                status=status.HTTP_409_CONFLICT,
            )


class LocationViewSet(ProtectedDestroyMixin, viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class RideModeViewSet(viewsets.ReadOnlyModelViewSet):
    """The rate card. Lookup by mode_code — /api/modes/TRICYCLE/."""

    queryset = RideModeLookup.objects.all()
    serializer_class = RideModeSerializer
    lookup_field = "mode_code"


class LGUUnitViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LGUUnit.objects.all()
    serializer_class = LGUUnitSerializer
    lookup_field = "lgu_code"
```

**Key fix from review**: `LGUUnit` is imported from `apps.accounts.models`.

Read-only is a deliberate scope cut, not an omission: `RIDE_MODE` and
`LGU_UNIT` are reference data. Rates change through the admin or a seed edit —
that is D-62's entire point — so the API exposes no write path to undermine it.

---

### 6. The driver-scoped serializers and viewsets (~25 min)

**Merge imports to the top of `backend/apps/accounts/serializers.py`** (the
existing auth serializers already have the top import block — add the new
imports there, do not create a second import block):

```python
# At the top of the file, merged with existing imports:
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import PHONE_VALIDATOR, Accreditation, LGUUnit, Vehicle
from apps.core.enums import UserRole
from apps.rides.models import RideModeLookup
```

Then append the two serializer classes at the end of the file:

```python
class VehicleSerializer(serializers.ModelSerializer):
    mode = serializers.SlugRelatedField(
        slug_field="mode_code", queryset=RideModeLookup.objects.all()
    )
    driver = serializers.SerializerMethodField()

    class Meta:
        model = Vehicle
        fields = ["id", "driver", "mode", "plate_number", "model",
                  "capacity", "route_info"]
        read_only_fields = ["id", "driver"]

    def get_driver(self, obj):
        return obj.driver.user.full_name


class AccreditationSerializer(serializers.ModelSerializer):
    lgu = serializers.SlugRelatedField(
        slug_field="lgu_code", queryset=LGUUnit.objects.all()
    )
    driver = serializers.SerializerMethodField()
    is_valid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Accreditation
        fields = ["id", "driver", "lgu", "badge_no", "status",
                  "expiry_date", "badge_visible", "is_valid"]
        read_only_fields = ["id", "driver"]

    def get_driver(self, obj):
        return obj.driver.user.full_name

    def validate_expiry_date(self, value):
        if value < timezone.localdate():
            raise serializers.ValidationError("The badge's expiry date is in the past.")
        return value
```

Two notes:

- `is_valid` is the model's *property* (status VERIFIED and not expired), and
  properties are never auto-mapped by `ModelSerializer` — it must be declared
  as an explicit read-only field or DRF raises.
- `status` is writable on purpose. In a real deployment the LGU issues the
  badge; here the driver records it, which is the simulated-administration
  path the demo needs. The `ChoiceField` generated from the model still bounds
  it to the enum.

**Merge imports to the top of `backend/apps/accounts/views.py`** (same
pattern — one import block at the top):

```python
# At the top of the file, merged with existing imports:
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import Accreditation, Vehicle
from apps.accounts.permissions import IsDriver
from apps.accounts.serializers import (
    AccreditationSerializer,
    LoginSerializer,
    MeSerializer,
    OtpRequestSerializer,
    OtpVerifySerializer,
    RegisterSerializer,
    VehicleSerializer,
)
from apps.accounts.services import OtpService, RegistrationService
```

Then append the two viewset classes at the end of the file:

```python
class VehicleViewSet(viewsets.ModelViewSet):
    """A driver's vehicle. The driver is always the caller — never a body field."""

    permission_classes = [IsDriver]
    serializer_class = VehicleSerializer

    def get_queryset(self):
        return Vehicle.objects.filter(driver=self.request.user.driver_profile)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user.driver_profile)


class AccreditationViewSet(viewsets.ModelViewSet):
    """Sertipikadong Manong — a driver's own LGU badges."""

    permission_classes = [IsDriver]
    serializer_class = AccreditationSerializer

    def get_queryset(self):
        return Accreditation.objects.filter(driver=self.request.user.driver_profile)

    def perform_create(self, serializer):
        serializer.save(driver=self.request.user.driver_profile)
```

`perform_create` assigning `driver` from the token is the security-relevant
line: the authenticated caller can never create a vehicle or badge for someone
else, because the serializer never accepts a `driver` input at all.

---

### 7. The routers (~10 min)

Create `backend/apps/rides/urls.py`:

```python
from rest_framework.routers import SimpleRouter

from apps.rides.views import LGUUnitViewSet, LocationViewSet, RideModeViewSet

router = SimpleRouter()
router.register("locations", LocationViewSet, basename="locations")
router.register("modes", RideModeViewSet, basename="modes")
router.register("lgus", LGUUnitViewSet, basename="lgus")

urlpatterns = router.urls
```

And **replace** `backend/apps/accounts/urls.py` with the complete final file
(auth routes from Step 3.01 first, then the driver-scoped router):

```python
"""Account-domain routes — Step 3.01 auth + Step 3.02 driver assets."""

from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.accounts.views import (
    AccreditationViewSet,
    LoginView,
    MeView,
    OtpRequestView,
    OtpVerifyView,
    RegisterView,
    VehicleViewSet,
)

router = SimpleRouter()
router.register("driver/vehicles", VehicleViewSet, basename="driver-vehicles")
router.register("driver/accreditations", AccreditationViewSet, basename="driver-accreditations")

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/refresh/", LoginView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/otp/request/", OtpRequestView.as_view(), name="otp-request"),
    path("auth/otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
    *router.urls,
]
```

**`SimpleRouter`, not `DefaultRouter`.** Two routers included under the same
`api/` prefix would each mount an `api-root` view at `""` and the URL names
would collide. Swagger replaces the browsable root anyway — one reason it is
the better navigation surface for this project.

---

### 8. The API tests (~40 min)

Create `backend/tests/test_core_api.py` — 14 tests:

```python
"""Core-entity API tests — Step 3.02: locations, modes, LGUs, driver assets."""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Accreditation, Vehicle


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def pax_api(api, passenger_user):
    api.force_authenticate(user=passenger_user)
    return api


@pytest.fixture
def driver_api(api, driver_user):
    api.force_authenticate(user=driver_user)
    return api


LOCATION_PAYLOAD = {
    "street": "12 Rizal St", "barangay": "Poblacion", "city": "Cabuyao",
    "province": "Laguna", "latitude": "14.276400", "longitude": "121.124500",
}


# ── Locations ─────────────────────────────────────────────────

def test_locations_require_authentication(api):
    assert api.post("/api/locations/", LOCATION_PAYLOAD, format="json").status_code == 401


def test_location_create_and_retrieve(pax_api):
    response = pax_api.post("/api/locations/", LOCATION_PAYLOAD, format="json")
    assert response.status_code == 201, response.data
    detail = pax_api.get(f"/api/locations/{response.data['id']}/")
    assert detail.status_code == 200
    assert detail.data["city"] == "Cabuyao"


def test_location_rejects_an_out_of_range_latitude(pax_api):
    payload = {**LOCATION_PAYLOAD, "latitude": "999"}
    response = pax_api.post("/api/locations/", payload, format="json")
    assert response.status_code == 400
    assert "latitude" in response.data


def test_location_delete_without_references(pax_api):
    created = pax_api.post("/api/locations/", LOCATION_PAYLOAD, format="json")
    assert pax_api.delete(f"/api/locations/{created.data['id']}/").status_code == 204


def test_location_delete_referenced_by_a_ride(pax_api, locations, ride):
    home, _, _ = locations
    response = pax_api.delete(f"/api/locations/{home.id}/")
    assert response.status_code == 409
    assert "referenced" in response.data["detail"]


# ── Lookups are read-only ─────────────────────────────────────

def test_ride_modes_are_listed_but_not_writable(pax_api, tricycle):
    assert pax_api.get("/api/modes/").status_code == 200
    assert pax_api.post("/api/modes/", {}, format="json").status_code == 405


def test_ride_mode_retrieves_by_code_with_the_booking_fee(pax_api, tricycle):
    response = pax_api.get("/api/modes/TRICYCLE/")
    assert response.status_code == 200
    assert response.data["booking_fee"] == "3.00"   # D-64, read from the row


def test_lgus_are_listed(pax_api, lgu):
    response = pax_api.get("/api/lgus/")
    assert response.status_code == 200
    assert response.data["count"] == 1


# ── Driver-scoped assets ──────────────────────────────────────

def test_passenger_cannot_create_a_vehicle(pax_api, tricycle):
    payload = {"mode": tricycle.mode_code, "plate_number": "PAX 0001", "model": "Honda TMX"}
    assert pax_api.post("/api/driver/vehicles/", payload, format="json").status_code == 403


def test_driver_registers_a_vehicle_with_driver_assigned(driver_api, driver, tricycle):
    payload = {"mode": tricycle.mode_code, "plate_number": "ABC 1234",
               "model": "Honda TMX", "capacity": 3}
    response = driver_api.post("/api/driver/vehicles/", payload, format="json")
    assert response.status_code == 201, response.data
    vehicle = Vehicle.objects.get(plate_number="ABC 1234")
    assert vehicle.driver == driver
    listed = driver_api.get("/api/driver/vehicles/").data["results"]
    assert [v["plate_number"] for v in listed] == ["ABC 1234"]


def test_driver_records_an_lgu_badge(driver_api, driver, lgu):
    payload = {"lgu": lgu.lgu_code, "badge_no": "BDG-9001", "status": "VERIFIED",
               "expiry_date": str(timezone.localdate() + timedelta(days=365))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 201, response.data
    assert response.data["is_valid"] is True
    assert Accreditation.objects.filter(driver=driver, badge_no="BDG-9001").exists()


def test_accreditation_rejects_a_past_expiry(driver_api, lgu):
    payload = {"lgu": lgu.lgu_code, "badge_no": "BDG-9002", "status": "VERIFIED",
               "expiry_date": str(timezone.localdate() - timedelta(days=1))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 400
    assert "expiry_date" in response.data


def test_accreditation_rejects_an_unknown_lgu(driver_api):
    payload = {"lgu": "NOPE-XX", "badge_no": "BDG-9003",
               "expiry_date": str(timezone.localdate() + timedelta(days=30))}
    response = driver_api.post("/api/driver/accreditations/", payload, format="json")
    assert response.status_code == 400


# ── The M3 proof surface ──────────────────────────────────────

def test_the_schema_and_swagger_render(pax_api):
    schema = pax_api.get("/api/schema/")
    assert schema.status_code == 200
    assert schema["Content-Type"].startswith("application/vnd.oai.openapi")
    # The auth endpoints from Step 3.01 must appear with their request bodies.
    assert "/api/auth/login/" in schema.content.decode()
    assert pax_api.get("/api/docs/").status_code == 200
```

**Fixture note**: The `tricycle` fixture in `conftest.py` now includes
`booking_fee=Decimal("3.00")` (added in the review fix). The seed data
`seed_lookups.py` also sets `booking_fee=3.00` on all modes per D-64, so the
live Swagger walk will show the correct value.

Two things to notice:

- **The fixtures come from Phase 2's `conftest.py` unchanged** — `passenger`,
  `driver`, `tricycle`, `lgu`, `locations`, `ride`. The test database is created
  from migrations only, so nothing is seeded; the tests create exactly the
  lookup rows they need, which is also why the mode tests take the `tricycle`
  fixture.
- **`test_location_delete_referenced_by_a_ride` is the PROTECT check as an API
  behaviour** — the same integrity Phase 2 proved at the model level, now
  surfaced as a 409 a client can act on.

---

### 9. Run them (~15 min)

```powershell
Set-Location backend
..\.venv\Scripts\Activate.ps1
pytest tests/test_core_api.py -v
```

Expected: **14 passed**. Then the lint gate and the whole suite:

```powershell
..\.venv\Scripts\ruff check apps tests
pytest -q
```

Expected: ruff clean, **153 passed** (122 + 17 + 14).

---

### 10. Walk it in Swagger (~10 min)

With `runserver` up:

1. Open `http://127.0.0.1:8000/api/docs/`
2. Click **Authorize**, paste `Bearer <access>` from a register/login call
3. `POST /api/locations/` with the LOCATION_PAYLOAD body → 201
4. `GET /api/modes/TRICYCLE/` → the rate card with `booking_fee: "3.00"`
5. Log in as a driver (register one via `POST /api/auth/register/` with
   `role: "DRIVER"` and a `license_number`), re-Authorize, then
   `POST /api/driver/vehicles/` → 201 with `driver` filled from the token

This is the M3 habit, now established: every endpoint demonstrable without an
editor.

---

## Verify

- [ ] `pytest` → **153 passed** (122 + 17 + 14), 0 failures
- [ ] `ruff check apps tests` → clean
- [ ] `/api/docs/` renders; Authorize accepts the JWT; every endpoint shows a request schema
- [ ] Locations: full CRUD, out-of-range coordinates 400, referenced delete 409
- [ ] Modes and LGUs: list/retrieve only — a POST gets 405
- [ ] Vehicles and accreditations: driver-scoped from the token; a passenger gets 403
- [ ] `booking_fee` reads "3.00" from the seeded row (D-64)
- [ ] No view contains logic beyond wiring — the only "rules" here are declared validators

---

## Log it

In `steps/PROGRESS.md`, on the row for the day you execute it:

```markdown
· Step 3.02 — serializers, viewsets, Swagger: locations CRUD (PROTECT → 409),
read-only modes/LGUs, driver-scoped vehicles/accreditations via IsDriver +
perform_create, schema + Swagger UI wired, auth endpoints documented for
OpenAPI; 14 API tests — 153 passed, 0 failures.
```

Tick the overview's step table, then commit:

```powershell
Set-Location ..
git add backend/ steps/
git commit -m "feat(api): add core-entity viewsets and the Swagger UI"
git push
```

---

## If it goes wrong

| Symptom | Cause | Fix |
|---|---|---|
| `/api/docs/` 404s | Schema route missing, or `url_name` mismatch | The Swagger view's `url_name="schema"` must equal the schema route's `name=` |
| `Reverse for 'api-root' not found` / duplicate name error | Two `DefaultRouter`s under one `api/` prefix | Use `SimpleRouter` (section 7) — Swagger replaces the browsable root |
| Everything but auth 401s | The global default `IsAuthenticated` | Intended. Use `force_authenticate` in tests and **Authorize** in Swagger |
| `Object with mode_code=… does not exist` | The body passed a UUID where a natural key is expected | `mode`/`lgu` take the code (`"TRICYCLE"`, `"CBO-LAG"`), not the PK |
| List assertions fail although the data is there | Global pagination wraps lists in `{"count", "results"}` | Read `response.data["results"]` |
| Vehicle POST 500: `Driver matching query does not exist` | The caller has role DRIVER but no Driver row | Register through the API (Step 3.01 creates the profile); don't hand-insert a bare user |
| `is_valid` raises during schema generation | A model property can't be auto-mapped | Declare it: `is_valid = serializers.BooleanField(read_only=True)` |
| Swagger shows auth endpoints with no request body | Step 3.01's APIViews lack schema info | The `@extend_schema` decorators in section 2 |
| Schema endpoint 500s on a serializer | An explicit field clashes with a model field name | Read the traceback's serializer name; the usual culprit is a property included without an explicit field |
| **Vehicle POST 500: `Vehicle matching query does not exist` (OneToOne)** | A driver already has a vehicle; the OneToOne PK=FK blocks a second | The model enforces one vehicle per driver. Use PATCH on the existing vehicle or delete it first. This is by design — one driver = one active vehicle. |
| **Accreditation POST 500: `Accreditation matching query does not exist` (OneToOne)** | A driver already has an accreditation for that LGU | Same OneToOne design. Use PATCH on the existing badge or change the LGU. |

---

## After this step

The API's foundation is laid: tokens, documented shapes, reference data, and
driver identity. Everything from here is domain logic on top — and the rate
card the next step needs is already reachable at `/api/modes/TRICYCLE/`.

Next: **Step 3.03 — FareCalculator**: base fare + per-km + booking fee +
Pakyawan split + surge multiplier, as a service class with unit tests.