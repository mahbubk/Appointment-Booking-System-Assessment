"""
Purpose for envelope renderer.
"""

from rest_framework.renderers import JSONRenderer


class EnvelopeRenderer(JSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        response = renderer_context.get("response")
        status_code = response.status_code if response else 200

        if status_code >= 400:
            errors = self._extract_errors(data)
            envelope = {"data": None, "errors": errors, "meta": None}
            return super().render(envelope, accepted_media_type, renderer_context)

        if isinstance(data, dict) and "data" in data and "meta" in data and "errors" in data:
            return super().render(data, accepted_media_type, renderer_context)

        envelope = {"data": data, "errors": [], "meta": None}
        return super().render(envelope, accepted_media_type, renderer_context)

    @staticmethod
    def _extract_errors(data) -> list:
        errors = []
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
        return errors or [{"message": "An unexpected error occurred."}]