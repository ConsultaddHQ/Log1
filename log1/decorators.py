from functools import wraps
from django.db.models import Q
from django.contrib.contenttypes.models import ContentType

from log1.permission import filter_attributes


def apply_query_filter(model):
    """
    Decorator to apply a query filter directly on a model, filtering based on request data.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, request, *args, **kwargs):
            # Default to an empty Q object if query_filter is not provided
            query_filter = eval(getattr(request, 'query_filter', "Q()"))

            try:
                # Ensure the query_filter is a Q object
                if not isinstance(query_filter, Q):
                    raise TypeError(f"query_filter must be a Q object, got {type(query_filter).__name__} instead.")

                # Apply the filter directly on the model
                filtered_queryset = model.objects.filter(query_filter)

                # Add the filtered queryset to kwargs for further processing
                kwargs['queryset'] = filtered_queryset
            except Exception as e:
                raise ValueError(f"Error applying query filter: {query_filter}. Error: {str(e)}")

            return func(self, request, *args, **kwargs)

        return wrapper

    return decorator


def prefetch_filtered_attributes(serializer_class):
    """
    Decorator to prefetch filtered attributes for a serializer.

    Args:
        serializer_class (class): The serializer class to decorate.
    """
    original_init = serializer_class.__init__

    @wraps(original_init)
    def new_init(self, *args, **kwargs):
        # Call the original __init__ method
        original_init(self, *args, **kwargs)

        # Precompute and cache filtered attributes in the context
        user = self.context['request'].user
        model_class = self.Meta.model  # Assumes Meta.model is defined in the serializer
        content_type = ContentType.objects.get_for_model(model_class)
        # Determine ownership if applicable
        instance = self.context.get('instance')
        is_owner = instance and hasattr(instance, 'created_by') and instance.created_by == user

        # Fetch and cache attributes
        self.context['filtered_attributes'] = filter_attributes(
            user=user,
            content_type=content_type,
            data={},  # Empty dict, just to fetch attributes
            is_owner=is_owner
        )

    serializer_class.__init__ = new_init
    return serializer_class
