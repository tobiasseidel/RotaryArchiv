# T3-auth-konzept.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** project-brief_v03.md, T2-migrations-plan.md  
> **Input für:** T6 Coding (Backend B), T5 Frontend/Design
>
> **⚠️ Aktualisiert durch T9-dev-strategie.md:** Dieses Dokument platziert die
> Auth-Implementierung in einem separaten `backend_b`-Service mit `rotary_core`-Dependency.
> Laut T9 wird in Phase 1 mit **einem Single-Backend** entwickelt — Auth läuft
> zunächst im selben Prozess. Die Backend-B-Struktur bleibt als Zukunftsplan gültig.
> Siehe [T9-dev-strategie.md](T9-dev-strategie.md).

---

## Kontext & Anforderungen

Aus T1 (Archetypen) und T2 (Datenmodell) ergeben sich folgende Auth-Anforderungen:

| Anforderung | Quelle |
|---|---|
| Anonyme Besucher dürfen `is_public=True`-Inhalte lesen | T1 Jannik, Karoline |
| Eingeloggte Nutzer sehen mehr (90er-Inhalte nach Freischaltung) | T1 Wolfgang, Dr. Miriam |
| Anonyme Beiträge (Story/Korrektur) ohne Login möglich | T1 Beitragsmodell |
| Beiträge eingeloggter Nutzer sind direkt sichtbar (kein Moderationswarteschlange) | T1 |
| Admin-Moderation-Queue nur für Admins | T2 P4 Endpoints |
| Kein komplexes Rollen-System nötig — zwei Stufen: User / Admin | Project Brief |

---

## Entscheidung: JWT (Stateless)

**Gewählt: JWT mit Access + Refresh Token.**

| Option | Pro | Contra | Urteil |
|---|---|---|---|
| **JWT** | Stateless, kein Session-Store, skalierbar, einfach in FastAPI | Token-Invalidierung komplex | ✅ Gewählt |
| Session-Cookies | Einfache Invalidierung | Braucht Redis/DB-Session-Store, komplexer auf NAS | ❌ |
| API-Key (statisch) | Sehr einfach | Kein User-Kontext, kein Logout möglich | ❌ nur für interne Dienste |

**Begründung:** Das System läuft auf einer NAS ohne externen Session-Store.
JWT erfordert keine zusätzliche Infrastruktur. Da das Nutzervolumen klein ist
(Vereinsmitglieder, nicht Tausende), sind die Nachteile von JWT vernachlässigbar.

---

## Token-Design

### Access Token (JWT)

```
Header:  { "alg": "HS256", "typ": "JWT" }
Payload: {
  "sub":   "42",                    ← user_id (Integer als String)
  "email": "w.mueller@example.de",
  "role":  "admin",                 ← "user" | "admin"
  "iat":   1746000000,
  "exp":   1746003600               ← 60 Minuten
}
```

- **Signatur:** HMAC-SHA256 mit `JWT_SECRET_KEY` (256-Bit aus .env)
- **Laufzeit:** 60 Minuten (konfigurierbar via `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`)
- **Inhalt:** Minimale Claims — nur was im Request gebraucht wird

### Refresh Token

- Opaque String (32 Byte Hex, sicher generiert)
- In PostgreSQL gespeichert (`refresh_tokens`-Tabelle, s.u.)
- Laufzeit: 30 Tage (konfigurierbar via `JWT_REFRESH_TOKEN_EXPIRE_DAYS`)
- Rotation: Bei jedem Refresh wird ein neuer Refresh Token ausgegeben, der alte ungültig

### Token-Flow

```
[Login]
  POST /api/v1/auth/login {email, password}
  → 200 {access_token, refresh_token, expires_in}

[Authentifizierter Request]
  GET /api/v1/persons/mueller-hans-1891
  Authorization: Bearer <access_token>
  → Backend prüft JWT-Signatur + exp

[Token erneuern]
  POST /api/v1/auth/refresh {refresh_token}
  → 200 {access_token, refresh_token}  ← neues Token-Paar

[Logout]
  POST /api/v1/auth/logout {refresh_token}
  → Refresh Token in DB als revoked markieren
  → 204 No Content
```

---

## Datenbankmodell (User + Refresh Tokens)

Diese Tabellen kommen in `rotary_core/models.py` (Schema-Hoheit: Backend A).

```python
import secrets
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id           = Column(Integer, primary_key=True, index=True)
    email        = Column(String(255), nullable=False, unique=True, index=True)
    display_name = Column(String(255), nullable=False)
    # Passwort: bcrypt-Hash (niemals Plaintext speichern)
    password_hash = Column(String(255), nullable=False)
    role          = Column(String(20), nullable=False, default="user")
    # Erlaubte Werte: "user" | "admin"
    is_active     = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at    = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at    = Column(DateTime, server_default=func.now(),
                           onupdate=func.now(), nullable=False)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"),
                        nullable=False, index=True)
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    # token_hash = SHA-256 des opaque Tokens — nie Plaintext speichern
    issued_at  = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    revoked    = Column(Boolean, nullable=False, default=False, server_default="0")
    revoked_at = Column(DateTime, nullable=True)
    # User-Agent für Audit (optional aber empfohlen)
    user_agent = Column(String(512), nullable=True)
```

---

## FastAPI-Implementierung (Backend B)

### Abhängigkeiten (`backend_b/pyproject.toml`)

```toml
dependencies = [
    "rotary-core @ file:../../packages/rotary_core",
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "sqlalchemy>=2.0",
    "python-jose[cryptography]>=3.3",   # JWT
    "passlib[bcrypt]>=1.7",             # Passwort-Hashing
    "python-multipart>=0.0.9",          # Form-Daten für Login
]
```

### `backend_b/src/rotary_public/auth/dependencies.py`

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from rotary_core.database import get_db
from rotary_core.models import User
from .config import settings

security = HTTPBearer(auto_error=False)

def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User | None:
    """
    Optionale Authentifizierung.
    Gibt None zurück wenn kein/ungültiges Token — kein Fehler.
    Wird für alle öffentlichen Endpoints verwendet.
    """
    if credentials is None:
        return None
    return _decode_token(credentials.credentials, db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        HTTPBearer(auto_error=True)
    ),
    db: Session = Depends(get_db),
) -> User:
    """
    Pflicht-Authentifizierung. Wirft 401 wenn kein Token.
    """
    user = _decode_token(credentials.credentials, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Admin-Pflicht. Wirft 403 wenn kein Admin."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


def _decode_token(token: str, db: Session) -> User | None:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = int(payload.get("sub", 0))
        if not user_id:
            return None
    except (JWTError, ValueError):
        return None

    user = db.query(User).filter(
        User.id == user_id, User.is_active == True
    ).first()
    return user
```

### `backend_b/src/rotary_public/api/auth.py` (Router)

```python
from datetime import datetime, timedelta, timezone
import hashlib, secrets
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from rotary_core.database import get_db
from rotary_core.models import User, RefreshToken
from ..auth.dependencies import get_current_user
from ..auth.config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not pwd_context.verify(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültige Zugangsdaten",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Konto deaktiviert")

    access_token = _create_access_token(user)
    refresh_token, refresh_hash = _create_refresh_token()
    _store_refresh_token(db, user.id, refresh_hash)

    return {
        "access_token":  access_token,
        "refresh_token": refresh_token,
        "token_type":    "bearer",
        "expires_in":    settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post("/refresh")
def refresh(body: dict, db: Session = Depends(get_db)):
    token = body.get("refresh_token", "")
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
        RefreshToken.expires_at > datetime.now(timezone.utc),
    ).first()

    if not stored:
        raise HTTPException(status_code=401, detail="Ungültiger Refresh Token")

    # Token-Rotation: alten invalidieren
    stored.revoked = True
    stored.revoked_at = datetime.now(timezone.utc)

    user = db.query(User).filter(User.id == stored.user_id).first()
    new_access = _create_access_token(user)
    new_refresh, new_hash = _create_refresh_token()
    _store_refresh_token(db, user.id, new_hash)
    db.commit()

    return {"access_token": new_access, "refresh_token": new_refresh, "token_type": "bearer"}


@router.post("/logout", status_code=204)
def logout(body: dict, db: Session = Depends(get_db)):
    token = body.get("refresh_token", "")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    if stored:
        stored.revoked = True
        stored.revoked_at = datetime.now(timezone.utc)
        db.commit()


# ─── Hilfsfunktionen ────────────────────────────────────────────────────────

def _create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user.id), "email": user.email,
         "role": user.role, "exp": expire},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

def _create_refresh_token() -> tuple[str, str]:
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash

def _store_refresh_token(db: Session, user_id: int, token_hash: str):
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    db.add(RefreshToken(user_id=user_id, token_hash=token_hash, expires_at=expires))
    db.commit()
```

---

## Zugriffsmatrix

| Endpoint | Anonym | User (eingeloggt) | Admin |
|---|---|---|---|
| `GET /api/v1/persons/{slug}` (is_public=True) | ✅ voll | ✅ voll | ✅ voll |
| `GET /api/v1/persons/{slug}` (is_public=False) | ✅ Stub | ✅ voll | ✅ voll |
| `GET /api/v1/documents/{id}` (is_public=False) | ✅ Stub | ✅ voll | ✅ voll |
| `POST /api/v1/stories` | ✅ → Moderation-Queue | ✅ → direkt sichtbar | ✅ |
| `POST /api/v1/corrections` | ✅ → Moderation-Queue | ✅ → direkt sichtbar | ✅ |
| `GET /api/v1/admin/moderation-queue` | ❌ 401 | ❌ 403 | ✅ |
| `POST /api/v1/admin/stories/{id}/approve` | ❌ 401 | ❌ 403 | ✅ |

> **Stub-Response:** Nicht-öffentliche Objekte geben HTTP 200 mit
> `{"stub": true, "id": ..., "type": "person", "hint": "Dieses Profil ist noch nicht öffentlich."}` zurück.
> **Kein 403, kein 404** — Progressive Disclosure wie in T1 definiert.

---

## Nutzer-Management (Bootstrap)

Da kein Self-Registration-Flow geplant ist, werden Nutzer vom Admin angelegt.
Bootstrap-Skript für den ersten Admin:

```python
# scripts/create_admin.py
# Aufruf: docker exec rotary_backend_a python /app/scripts/create_admin.py

import os
from passlib.context import CryptContext
from rotary_core.database import SessionLocal
from rotary_core.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

db = SessionLocal()
admin = User(
    email        = os.environ["ADMIN_EMAIL"],
    display_name = "Administrator",
    password_hash = pwd_context.hash(os.environ["ADMIN_PASSWORD"]),
    role         = "admin",
    is_active    = True,
)
db.add(admin)
db.commit()
print(f"✅ Admin erstellt: {admin.email}")
```

Aufruf einmalig nach erstem Deploy:
```bash
docker exec -e ADMIN_EMAIL=admin@rotary-dresden.de \
            -e ADMIN_PASSWORD=SICHERES_PASSWORT \
            rotary_backend_a python /app/scripts/create_admin.py
```

---

*Nächste Datei: T3-email-verschluesselung.md*
