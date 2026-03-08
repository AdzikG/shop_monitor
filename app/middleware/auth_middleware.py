from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

from core.auth_core import get_session, SESSION_COOKIE

EXEMPT_PATHS = {"/auth/login", "/auth/logout", "/auth/setup"}
STATIC_PREFIXES = ("/static/", "/screenshots/")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        method = request.method

        # GET jest zawsze publiczne
        if method == "GET":
            return await call_next(request)

        # Ścieżki zwolnione z auth
        if path in EXEMPT_PATHS:
            return await call_next(request)

        # Pliki statyczne
        if any(path.startswith(p) for p in STATIC_PREFIXES):
            return await call_next(request)

        token = request.cookies.get(SESSION_COOKIE)
        session = get_session(token)

        if not session:
            return RedirectResponse(f"/auth/login?next={path}", status_code=303)

        # DELETE lub POST /*.../delete → tylko admin
        is_delete = method == "DELETE" or (method == "POST" and path.endswith("/delete"))
        if is_delete and session.get("role") != "admin":
            return Response("Brak uprawnień (wymagana rola admin)", status_code=403)

        return await call_next(request)
