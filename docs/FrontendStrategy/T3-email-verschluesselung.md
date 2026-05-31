# T3-email-verschluesselung.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** T2-migrations-plan.md (P3: Story, Correction), T3-auth-konzept.md  
> **Input für:** T6 Coding (P3), rotary_core

---

## Problem

Story- und Correction-Einreichungen können eine E-Mail-Adresse des Einreichers
enthalten (`author_email_enc` in `stories` und `corrections`). Diese Adresse:

- darf **nie im Klartext in der DB** gespeichert sein (Datenschutz, DSGVO)
- muss vom Admin **lesbar** sein (für Rückfragen zum Beitrag)
- wird **niemals im Frontend angezeigt** — nur intern durch Admin

Das schließt One-Way-Hashing (bcrypt etc.) aus. Es muss **reversible Verschlüsselung** sein.

---

## Entscheidung: Fernet (symmetrisch)

**Gewählt: Fernet (AES-128-CBC + HMAC-SHA256)**

| Option | Symmetrisch | Schlüssel-Mgmt | Decryptable | Urteil |
|---|---|---|---|---|
| **Fernet** (cryptography-lib) | ✅ | 1 Schlüssel in .env | ✅ | ✅ Gewählt |
| RSA/PGP asymmetrisch | ❌ | Private Key sicher lagern | ✅ | Overkill für NAS-Projekt |
| AES-GCM manuell | ✅ | 1 Schlüssel | ✅ | Fernet ist sicherer Wrapper dafür |
| bcrypt / argon2 | — | — | ❌ | Nur für Passwörter |

**Begründung:** Fernet ist ein sicheres, etabliertes Format aus der
`cryptography`-Bibliothek (bereits als FastAPI-Dependency vorhanden).
Es enthält Timestamp und HMAC — Manipulation wird erkannt.
Asymmetrische Verfahren wären für diesen Anwendungsfall unnötig komplex:
Es gibt keinen zweiten Akteur, der verschlüsseln, aber nicht entschlüsseln soll.

---

## Schlüssel-Generierung und -Speicherung

### Einmalige Schlüsselgenerierung

```python
# Einmalig auf der NAS ausführen, Ausgabe in .env eintragen
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
# Ausgabe: z.B. "rXt3...base64...=="  (44 Zeichen)
```

### .env-Eintrag

```bash
EMAIL_ENCRYPTION_KEY=rXt3_NUR_EINMAL_GENERIEREN_UND_NIE_AENDERN==
```

> ⚠️ **Kritisch:** Dieser Schlüssel darf sich **nie** ändern, solange
> verschlüsselte Daten in der DB existieren. Vor Schlüsselwechsel:
> alle Einträge mit altem Schlüssel entschlüsseln und neu verschlüsseln.

---

## Implementierung in `rotary_core`

### `rotary_core/crypto.py` (neue Datei)

```python
"""
E-Mail-Verschlüsselung für author_email_enc in Story/Correction.
Verwendet Fernet (AES-128-CBC + HMAC-SHA256).
"""
from cryptography.fernet import Fernet, InvalidToken
from .config import settings


def _get_fernet() -> Fernet:
    """Lazy-Init des Fernet-Objekts aus Settings."""
    return Fernet(settings.EMAIL_ENCRYPTION_KEY.encode())


def encrypt_email(plaintext_email: str) -> str:
    """
    Verschlüsselt eine E-Mail-Adresse.
    Gibt Base64-kodierten Ciphertext zurück (für TEXT-Spalte in DB).
    """
    if not plaintext_email:
        raise ValueError("E-Mail darf nicht leer sein")
    fernet = _get_fernet()
    return fernet.encrypt(plaintext_email.encode()).decode()


def decrypt_email(encrypted: str) -> str:
    """
    Entschlüsselt author_email_enc aus DB.
    Wirft ValueError bei ungültigem/manipuliertem Ciphertext.
    """
    try:
        fernet = _get_fernet()
        return fernet.decrypt(encrypted.encode()).decode()
    except InvalidToken as e:
        raise ValueError("E-Mail-Entschlüsselung fehlgeschlagen: ungültiger Token") from e


def is_email_encrypted(value: str) -> bool:
    """Heuristik: Fernet-Tokens beginnen immer mit 'gAAAAA'."""
    return value.startswith("gAAAAA")
```

---

## Verwendung in Backend B (Einreichungs-Endpunkte)

### Beim Speichern (POST /api/v1/stories)

```python
from rotary_core.crypto import encrypt_email
from rotary_core.models import Story, ContributionStatus

@router.post("/api/v1/stories", status_code=201)
def submit_story(
    body: StorySubmitRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    encrypted_email = None
    if body.author_email:
        encrypted_email = encrypt_email(body.author_email)

    # Eingeloggte User → direkt approved; Anonym → submitted (Moderation)
    initial_status = (
        ContributionStatus.APPROVED
        if current_user is not None
        else ContributionStatus.SUBMITTED
    )

    story = Story(
        title               = body.title,
        body                = body.body,
        author_name         = body.author_name,
        author_email_enc    = encrypted_email,   # Klartext-E-Mail niemals speichern
        status              = initial_status,
        is_public           = current_user is not None,
        related_entity_type = body.related_entity_type,
        related_entity_id   = body.related_entity_id,
        submitted_by_user   = current_user.id if current_user else None,
    )
    db.add(story)
    db.commit()
    return {"id": story.id, "status": story.status}
```

### Beim Lesen durch Admin (GET /api/v1/admin/moderation-queue)

```python
from rotary_core.crypto import decrypt_email

@router.get("/api/v1/admin/moderation-queue")
def get_moderation_queue(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),   # nur Admins
):
    pending = db.query(Story).filter(
        Story.status == ContributionStatus.SUBMITTED
    ).order_by(Story.created_at.asc()).all()

    result = []
    for story in pending:
        # E-Mail nur für Admin entschlüsseln — nie in öffentliche Responses
        author_email_plain = None
        if story.author_email_enc:
            try:
                author_email_plain = decrypt_email(story.author_email_enc)
            except ValueError:
                author_email_plain = "[Entschlüsselung fehlgeschlagen]"

        result.append({
            "id":           story.id,
            "title":        story.title,
            "author_name":  story.author_name,
            "author_email": author_email_plain,   # Klartext NUR in Admin-Response
            "submitted_at": story.created_at,
            "body_preview": story.body[:200],
        })
    return result
```

> ⚠️ `author_email_plain` **niemals** in öffentliche API-Responses einbauen.
> Nur in Admin-gesicherten Endpoints (`require_admin`-Dependency).

---

## Schlüsselrotation (Notfallverfahren)

Falls der Schlüssel kompromittiert wurde oder ein Wechsel nötig ist:

```python
# scripts/rotate_email_key.py
# Vor Ausführung: alten Schlüssel als OLD_KEY, neuen als NEW_KEY in Env setzen
import os
from cryptography.fernet import Fernet
from rotary_core.database import SessionLocal
from rotary_core.models import Story, Correction

old_fernet = Fernet(os.environ["OLD_EMAIL_ENCRYPTION_KEY"].encode())
new_fernet = Fernet(os.environ["NEW_EMAIL_ENCRYPTION_KEY"].encode())

db = SessionLocal()
count = 0

for model in [Story, Correction]:
    for obj in db.query(model).filter(model.author_email_enc.isnot(None)).all():
        try:
            plaintext = old_fernet.decrypt(obj.author_email_enc.encode()).decode()
            obj.author_email_enc = new_fernet.encrypt(plaintext.encode()).decode()
            count += 1
        except Exception as e:
            print(f"⚠️  Fehler bei {model.__name__} id={obj.id}: {e}")

db.commit()
print(f"✅ {count} E-Mail-Adressen re-verschlüsselt.")
```

---

## Bezug zur `rotary_core/config.py`

```python
# Ergänzung in rotary_core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # ... bestehende Settings ...
    EMAIL_ENCRYPTION_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
```

---

*Nächste Datei: T3-domain-entscheidung.md*
