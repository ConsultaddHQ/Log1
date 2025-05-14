from django.db.models import Q
from rest_framework.permissions import BasePermission

from employee.models import PermissionMetadata


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
        user_permissions = self.get_user_permissions(request.user, model_name, request.method)
        if not user_permissions:
            return False

        # Build dynamic context
        context = self.build_context(request)

        # Build query filters from permissions
        query_filter = self.build_query_filter(user_permissions, context)

        # Attach the filter to the request for view logic
        request.query_filter = query_filter
        return True

    @staticmethod
    def build_context(request):
        """
        Dynamically build the context from the request object.
        """
        return {
            "team_id": getattr(request.user.team, "id", None),
            "user_id": request.user.id,
        }

    @staticmethod
    def get_user_permissions(user, model_name, action):
        """
        Fetch the user's permissions for the current content type.
        """
        return PermissionMetadata.objects.filter(
            permission__content_type__model=model_name, permission__user=user, action=action
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

        query = Q()
        for perm in permissions:
            if perm.filter_string == "*":
                # Add an empty Q object to indicate no restrictions
                return Q()

            filter_string = perm.filter_string
            for placeholder, value in context.items():
                filter_string = filter_string.replace(f"<{placeholder}>", str(value))

            filter_q = Q(filter_string) if filter_string else Q()
            if perm.condition == "AND":
                query &= filter_q
            elif perm.condition == "NOT":
                query &= ~filter_q
            else:  # Default to OR
                query |= filter_q
        return query
