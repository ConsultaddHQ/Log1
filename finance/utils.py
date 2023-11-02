from rest_framework import status
from rest_framework.response import Response

from project.models import Leave

def check_access(request):
    if not ('superadmin' in request.user.roles or 'finance' in request.user.roles):
        return Response({"message": "You don't have access"}, status=status.HTTP_400_BAD_REQUEST)
    return None

def make_unique_preserve_order(ids):
    return list(dict.fromkeys(ids))


def return_leave_status(status, obj):
    if not status:
        leaves = Leave.objects.filter(consultant=obj)
        if leaves.filter(status = "pending"):
            return 'Pending 1st Level'
        elif leaves.filter(status = "applied"):
            return "Pending 2nd Level"
        elif leaves.filter(status = "rejected_1st_level"):
            return "Rejected 1st Level"
        elif  leaves.filter(status = "rejected"):
            return "Rejected"
        elif leaves.filter(status = "approved"):
            return "Approved"
    else:
        if status == "applied":
            return "Pending 2nd Level"
        elif status == "pending":
            return "Pending 1st Level"
        elif status == "rejected_1st_level":
            return "Rejected 1st Level"
        elif status == "rejected":
            return "Rejected"
        elif status == "approved":
            return "Approved"
        return None
