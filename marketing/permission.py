from functools import wraps
from django.http import Http404
from rest_framework.response import Response
from django.contrib.contenttypes.models import ContentType


def validate_permission(model_class):
    """
    Decorator to validate permissions dynamically for a given model.
    Handles object retrieval and permission checks based on request method.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            object_id = kwargs.get("pk")

            if not model_class:
                raise Http404("Model name or object ID not provided.")
            model_name = model_class._meta.model_name
            # try:
            #     content_type = ContentType.objects.get(model=model.lower())
            # except ContentType.DoesNotExist:
            #     raise Http404(f"Model '{model}' does not exist.")
            #
            # model_class = content_type.model_class()

            if object_id is not None:
                try:
                    instance = model_class.objects.get(id=object_id)
                except model_class.DoesNotExist:
                    raise Http404(f"Object with ID '{object_id}' does not exist in model {model_name}.")
            else:
                instance = None

            kwargs["instance"] = instance
            # Fetch permission validation logic for the model
            validate_func = MODEL_PERMISSION_VALIDATORS.get(model_name.lower(), {})
            # validate_func = permission_validators.get(request.method)
            if validate_func and not validate_func(request, instance):
                return Response({"message": "Permission Denied"}, status=403)

            return func(self, request, *args, **kwargs)
        return wrapper
    return decorator


def submission_permission_validator(request, instance):
    """
    Validate permissions for 'submission' model.
    """
    def validate_post():
        return "add_submission" in request.permissions

    def validate_put():
        return (
            "change_submission" in request.permissions or
            ("change_own_submission" in request.permissions and instance.created_by == request.user)
        )

    validators = {
        "POST": validate_post,
        "PUT": validate_put,
    }

    return validators.get(request.method, lambda: False)()


# Register permission validators for models
MODEL_PERMISSION_VALIDATORS = {
    "submission": submission_permission_validator
}
