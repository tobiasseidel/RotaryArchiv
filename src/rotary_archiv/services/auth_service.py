"""Auth Service - Business-Logic für Authentifizierung und Benutzerverwaltung."""

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from src.rotary_archiv.core.models import User, UserRole

# Passwort-Hashing mit bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Exceptions ──────────────────────────────────────────────────────────────


class AuthServiceError(Exception):
    """Basis-Exception für Auth-Service."""


class UserNotFoundError(AuthServiceError):
    def __init__(self, user_id: int | None = None, username: str | None = None):
        if user_id:
            super().__init__(f"Benutzer {user_id} nicht gefunden")
        else:
            super().__init__(f"Benutzer '{username}' nicht gefunden")


class UserConflictError(AuthServiceError):
    def __init__(self, username: str):
        super().__init__(f"Benutzername '{username}' bereits vergeben")


class InvalidCredentialsError(AuthServiceError):
    def __init__(self):
        super().__init__("Ungültige Anmeldedaten")


class InactiveUserError(AuthServiceError):
    def __init__(self, username: str):
        super().__init__(f"Benutzer '{username}' ist deaktiviert")


# ─── Service Functions ──────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    """Passwort hashen."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Passwort verifizieren."""
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Benutzer authentifizieren. Wirft Exception bei Fehler."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise InvalidCredentialsError()
    if not user.is_active:
        raise InactiveUserError(username)
    if not verify_password(password, user.password_hash):
        raise InvalidCredentialsError()
    return user


def create_user(
    db: Session,
    username: str,
    display_name: str,
    password: str,
    role: UserRole = UserRole.VIEWER,
) -> User:
    """Neuen Benutzer erstellen."""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise UserConflictError(username)

    user = User(
        username=username,
        display_name=display_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(
    db: Session,
    user_id: int,
    display_name: str | None = None,
    role: UserRole | None = None,
    is_active: bool | None = None,
    password: str | None = None,
) -> User:
    """Benutzer aktualisieren."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id=user_id)

    if display_name is not None:
        user.display_name = display_name
    if role is not None:
        user.role = role
    if is_active is not None:
        user.is_active = is_active
    if password is not None:
        user.password_hash = hash_password(password)

    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> None:
    """Benutzer löschen."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id=user_id)
    db.delete(user)
    db.commit()


def list_users(db: Session, include_inactive: bool = False) -> list[User]:
    """Alle Benutzer auflisten."""
    query = db.query(User)
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    return query.order_by(User.username).all()


def get_user(db: Session, user_id: int) -> User:
    """Einzelnen Benutzer laden."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(user_id=user_id)
    return user


def get_user_by_username(db: Session, username: str) -> User | None:
    """Benutzer nach Username laden."""
    return db.query(User).filter(User.username == username).first()


def ensure_admin_exists(db: Session) -> User:
    """Stellt sicher, dass ein Admin-Benutzer existiert. Erstellt einen Standard-Admin wenn nötig."""
    admin = db.query(User).filter(User.role == UserRole.ADMIN).first()
    if admin:
        return admin

    # Standard-Admin erstellen
    return create_user(
        db,
        username="admin",
        display_name="Administrator",
        password="admin",  # Muss nach dem ersten Login geändert werden!
        role=UserRole.ADMIN,
    )
