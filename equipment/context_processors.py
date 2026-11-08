"""Values every template can use."""

from .models import EquipmentRequest


def manager_badges(request):
    """Give managers the pending-request count for the navigation badge."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated and user.is_staff):
        return {}
    return {
        "nav_pending_total": EquipmentRequest.objects.filter(
            status=EquipmentRequest.Status.PENDING
        ).count()
    }
