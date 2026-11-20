from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wrap every DRF error as {"error": {"status", "message", "details"}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    details = response.data
    if isinstance(details, dict) and set(details) == {"detail"}:
        message, details = str(details["detail"]), None
    else:
        message = "Invalid request."
    response.data = {
        "error": {"status": response.status_code, "message": message, "details": details}
    }
    return response
