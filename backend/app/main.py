from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title="HH Control", version="0.1.0")
app.add_middleware(SessionMiddleware, secret_key=settings.app_session_secret, https_only=settings.cookie_secure,
                   same_site="lax", session_cookie="hh_control_session")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
