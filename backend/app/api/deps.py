from app.services import explain as explain_svc

# Single shared provider instance for the whole API surface -- avoids
# re-instantiating (and re-checking Granite credentials) per request.
provider = explain_svc.get_provider()
