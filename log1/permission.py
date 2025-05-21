import re

from django.db.models import Q
from rest_framework.permissions import BasePermission

from employee.models import PermissionMetadata
from consultant.models import Consultant, ConsultantMarketing


class RBACPermission(BasePermission):
    """
    Custom permission class that integrates with the CustomPermission model.
    """

    def has_permission(self, request, view, model_name=None):
        # Ensure the user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False

        # Determine the model name dynamically

        if not model_name:
            model_name = self.get_model_name(view)

        # Fetch relevant permissions for the user
        action = request.method
        user_permissions = self.get_user_permissions(request.user, model_name, action)
        request.permissions = list(user_permissions.values_list("permission__codename", flat=True))
        if not user_permissions:
            return False, request.permissions

        # Extract required placeholders from permissions
        required_placeholders = self.get_required_placeholders(user_permissions)

        # Build dynamic context for only required placeholders
        context = self.build_context(request, required_placeholders)

        # Build query filters from permissions
        query_filter = self.build_query_filter(user_permissions, context) if action == 'GET' else None

        # Attach the filter to the request for view logic
        request.query_filter = query_filter
        request.permissions = list(user_permissions.values_list("permission__codename", flat=True))
        return True

    @staticmethod
    def get_required_placeholders(permissions):
        """
        Extract all unique placeholders required by the permission filter strings.
        """
        placeholder_pattern = r"<(.*?)>"
        required_placeholders = set()

        for perm in permissions:
            matches = re.findall(placeholder_pattern, perm.filter_string)
            required_placeholders.update(matches)

        return required_placeholders

    @staticmethod
    def build_context(request, required_placeholders):
        """
        Dynamically build the context for only the required placeholders.
        """
        context = {}

        if "user_id" in required_placeholders:
            context["user_id"] = request.user.id

        if "team_id" in required_placeholders:
            context["team_id"] = getattr(request.user.team, "id", None)

        if "team_name" in required_placeholders:
            context["team_name"] = getattr(request.user.team, "name", None)

        if "associated_teams_id" in required_placeholders:
            context["associated_teams_id"] = list(
                request.user.associated_to.all().values_list("id", flat=True)
            )

        if "team_and_pool_consultant_ids" in required_placeholders:
            context["team_and_pool_consultant_ids"] = (
                list(request.user.marketed.filter(status='open').values_list('consultant_id')) +
                list(ConsultantMarketing.objects.filter(in_pool=True, status='open').values_list('consultant_id', flat=True))
            )

        return context

    @staticmethod
    def get_user_permissions(user, model_name, action):
        """
        Fetch the user's permissions for the current content type.
        """
        return PermissionMetadata.objects.filter(
            (Q(permission__user=user) | Q(permission__in=list(user.groups.all().values_list('permissions', flat=True)))),
            permission__content_type__model=model_name, action=action
        )

    @staticmethod
    def get_model_name(view):
        """
        Determine the model name for the current view.
        """
        # Check if the view explicitly provides a model name
        if hasattr(view, 'model_name') and view.model_name:
            return view.model_name.lower()

        # Otherwise, infer the model name from the queryset
        if hasattr(view, 'queryset') and view.queryset is not None:
            return view.queryset.model._meta.model_name.lower()

        # If no model name is available, return None
        return None

    @staticmethod
    def build_query_filter(permissions, context):
        """
        Combine filters based on permissions into a single Q object.
        """
        queries = []
        for perm in permissions:
            if perm.filter_string == "*":
                # No restriction: return an empty query string equivalent to allowing all
                return ""

            filter_string = perm.filter_string
            for placeholder, value in context.items():
                filter_string = filter_string.replace(f"<{placeholder}>", repr(value))

            if perm.condition == "NOT":
                queries.append(f"~{filter_string}")
            else:  # Default to AND/OR
                queries.append(f"{filter_string}")

        # Combine queries based on conditions
        if permissions[0].condition == "AND":
            combined_query = " & ".join(queries)
        elif permissions[0].condition == "OR":
            combined_query = " | ".join(queries)
        else:
            combined_query = " & ".join(queries)  # Default to AND

        return combined_query
