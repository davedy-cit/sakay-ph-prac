from rest_framework.routers import SimpleRouter

from apps.rides.views import LGUUnitViewSet, LocationViewSet, RideModeViewSet

router = SimpleRouter()
router.register("locations", LocationViewSet, basename="locations")
router.register("modes", RideModeViewSet, basename="modes")
router.register("lgus", LGUUnitViewSet, basename="lgus")

urlpatterns = router.urls