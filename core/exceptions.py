"""
Purpose for catching error
"""

import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)


def envelope_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        logger.exception("Unhandled exception: %s", exc)
        return Response(
            {
                "data": None,
                "errors": [{"message": "An unexpected error occurred."}],
                "meta": None,
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    errors = []
    data = response.data

    if isinstance(data, dict):
        for field, messages in data.items():
            if isinstance(messages, list):
                for msg in messages:
                    errors.append({"field": field, "message": str(msg)})
            else:
                errors.append({"field": field, "message": str(messages)})
    elif isinstance(data, list):
        for msg in data:
            errors.append({"message": str(msg)})
    else:
        errors.append({"message": str(data)})

    response.data = {"data": None, "errors": errors, "meta": None}
    return response