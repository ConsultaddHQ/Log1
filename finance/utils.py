from rest_framework import status
from rest_framework.response import Response


def check_access(request):
    if not ('superadmin' in request.user.roles or 'finance' in request.user.roles):
        return Response({"message": "You don't have access"}, status=status.HTTP_400_BAD_REQUEST)
    return None

def make_unique_preserve_order(ids):
    return list(dict.fromkeys(ids))


def return_leave_status(status):
    if status == "applied":
        return "Pending 2nd Level"
    elif status == "pending":
        return  "Pending 1st Level"
    elif status == "rejected_1st_level":
        return "Rejected 1st Level"
    elif status == "rejected":
        return "Rejected"
    elif status == "approved":
        return  "Approved"
    return None