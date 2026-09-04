"""
Auth API - Login, Logout, Benutzerverwaltung
"""

import base64
from datetime import datetime, timezone
import hashlib
import hmac
import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.rotary_archiv.api.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.rotary_archiv.core.database import get_db
from src.rotary_archiv.core.models import User, UserRole
from src.rotary_archiv.services.auth_service import (
    InactiveUserError,
    InvalidCredentialsError,
    UserConflictError,
    UserNotFoundError,
    authenticate_user,
    create_user,
    delete_user,
    get_user,
    list_users,
    update_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# ─── Session Management ──────────────────────────────────────────────────────

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "rotary-archiv-secret-change-in-production")
SESSION_COOKIE = "rotary_session"
SESSION_EXPIRE_HOURS = 24 * 7  # 7 Tage


def _create_session_token(user_id: int) -> str:
    """Erstelle ein einfaches Session-Token."""
    payload = f"{user_id}:{datetime.now(timezone.utc).isoformat()}"
    signature = hmac.new(
        SECRET_KEY.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    token_data = base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
    return token_data


def _verify_session_token(token: str) -> int | None:
    """Verifiziere Session-Token und gib user_id zurück."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        parts = decoded.rsplit(":", 1)
        if len(parts) != 2:
            return None
        payload, signature = parts
        expected_sig = hmac.new(
            SECRET_KEY.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        user_id_str = payload.split(":")[0]
        return int(user_id_str)
    except Exception:
        return None


# ─── Dependencies ──────────────────────────────────────────────────────────


def get_current_user(
    rotary_session: str | None = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Aktuellen User aus Session laden."""
    if not rotary_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht angemeldet",
        )
    user_id = _verify_session_token(rotary_session)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Session",
        )
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden oder deaktiviert",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Erfordert Admin-Rechte."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin-Rechte erforderlich",
        )
    return user


def require_editor(user: User = Depends(get_current_user)) -> User:
    """Erfordert Editor- oder Admin-Rechte."""
    if user.role not in (UserRole.ADMIN, UserRole.EDITOR):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Editor-Rechte erforderlich",
        )
    return user


# ─── Auth Endpoints ──────────────────────────────────────────────────────────


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Benutzer anmelden."""
    try:
        user = authenticate_user(db, request.username, request.password)
    except InvalidCredentialsError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Anmeldedaten",
        ) from err
    except InactiveUserError as err:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Benutzer deaktiviert",
        ) from err

    token = _create_session_token(user.id)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_EXPIRE_HOURS * 3600,
    )

    return LoginResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
def logout(response: Response):
    """Benutzer abmelden."""
    response.delete_cookie(key=SESSION_COOKIE)
    return {"message": "Erfolgreich abgemeldet"}


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """Aktuellen Benutzer abrufen."""
    return UserResponse.model_validate(user)


# ─── User Management (Admin) ──────────────────────────────────────────────────


@router.get("/users", response_model=list[UserResponse])
def list_all_users(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Alle Benutzer auflisten (nur Admin)."""
    users = list_users(db, include_inactive=include_inactive)
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_new_user(
    request: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Neuen Benutzer erstellen (nur Admin)."""
    try:
        role = UserRole(request.role)
        user = create_user(
            db,
            username=request.username,
            display_name=request.display_name,
            password=request.password,
            role=role,
        )
        return UserResponse.model_validate(user)
    except UserConflictError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(err),
        ) from err


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Benutzer-Details abrufen (nur Admin)."""
    try:
        user = get_user(db, user_id)
        return UserResponse.model_validate(user)
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_detail(
    user_id: int,
    request: UserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Benutzer aktualisieren (nur Admin)."""
    try:
        role = UserRole(request.role) if request.role else None
        user = update_user(
            db,
            user_id,
            display_name=request.display_name,
            role=role,
            is_active=request.is_active,
            password=request.password,
        )
        return UserResponse.model_validate(user)
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Benutzer löschen (nur Admin)."""
    try:
        delete_user(db, user_id)
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err


@router.post("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    password: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Passwort zurücksetzen (nur Admin)."""
    try:
        update_user(db, user_id, password=password)
        return {"message": "Passwort erfolgreich zurückgesetzt"}
    except UserNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err),
        ) from err
