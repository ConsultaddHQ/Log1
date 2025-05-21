from rest_framework.response import Response
from rest_framework import status as _status


def check_submission_permissions(request, submission=None):

    if request.method == "POST":
        if "add_submission" in request.permissions:
            return True

    # Check if the user has the 'change_submission' or 'change_own_submission' permission
    elif request.method == 'PUT':
        if "change_submission" in request.permissions:
            # User has full change permissions
            return True
        elif "change_own_submission" in request.permissions:
            # User has 'change_own_submission', check ownership
            if submission and submission.created_by == request.user:
                return True
            else:
                return False
        else:
            # User lacks the required permissions
            return False

    else:
        return False