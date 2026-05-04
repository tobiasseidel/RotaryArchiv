# T3-domain-entscheidung.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** T3-nginx-config.md, T3-docker-compose.md  
> **Input für:** T5 Frontend/Design, T6 Coding

---

## Kontext

Die Domain ist in `.env` als `ROTARY_DOMAIN` gesetzt und wird von Nginx,
Certbot und BibTeX-Export verwendet. Diese Datei dokumentiert die Optionen
und gibt eine Empfehlung — die finale Entscheidung liegt beim Projektinhaber.

---

## Optionen im Überblick

| Option | Domain-Beispiel | TLS | Aufwand | Empfehlung |
|---|---|---|---|---|
| **A — Subdomain beim Club** | `archiv.rotary-dresden.de` | Let's Encrypt (automatisch) | DNS-Eintrag beim Club-Admin | ✅ Empfohlen |
| **B — Eigene Domain** | `rotaryarchiv-dresden.de` | Let's Encrypt (automatisch) | Domain kaufen (~10€/Jahr) + DNS | ✅ Alternativ |
| **C — Synology DDNS** | `rotary.your-nas.synology.me` | Let's Encrypt via Synology | Kein DNS nötig | ⚠️ Fallback (NAS-Hersteller-Abhängigkeit) |
| **D — Nur intern** | `rotary.local` | Selbstsigniert | Kein öffentlicher Zugang | ❌ Nicht für öffentliches Frontend |

---

## Empfehlung: Option A — Subdomain beim Club

`archiv.rotary-dresden.de`

**Voraussetzungen:**
1. Rotary Club Dresden besitzt `rotary-dresden.de` (Annahme)
2. Club-Admin legt DNS-A-Record an: `archiv → [NAS-Public-IP]`
3. NAS-Router: Port 80 und 443 auf NAS-IP weiterleiten (Port-Forwarding)
4. Certbot holt TLS-Zertifikat automatisch (s. T3-docker-compose.md)

**Wenn NAS-IP dynamisch (kein statisches IP vom ISP):**
- Synology DDNS als Zwischenschicht: `archiv.your-nas.synology.me`
- Oder: DynDNS-Dienst (deSEC.io — kostenlos, DSGVO-konform) mit
  automatischem IP-Update über Synology Task Scheduler

---

## URL-Schema (relevant für T5/T6)

Die Domain beeinflusst folgende Stellen im Code:

| Stelle | Verwendung | Datei |
|---|---|---|
| Nginx `server_name` | Virtual-Host-Matching | `nginx/conf.d/rotary.conf` |
| Certbot `-d` Parameter | TLS-Zertifikat für genau diese Domain | `docker-compose.yml` |
| BibTeX-Export `url`-Feld | `https://{domain}/dokument/{id}` | Backend B, T2 P4 |
| CORS (falls nötig) | `Access-Control-Allow-Origin` | Nginx oder FastAPI |
| E-Mail-Templates | Rückantwort-URL in Moderations-Mails | Backend B (optional) |

Alle Stellen beziehen den Wert aus `settings.ROTARY_DOMAIN` (via `.env`) —
**keine Hardcodes im Code**.

---

## Checkliste vor Go-Live

```
[ ] DNS-A-Record gesetzt (oder DynDNS konfiguriert)
[ ] Port-Forwarding am Router: 80 → NAS, 443 → NAS
[ ] .env: ROTARY_DOMAIN gesetzt
[ ] Certbot-Container gestartet, Zertifikat erfolgreich ausgestellt
[ ] nginx -t (Konfigurationstest) erfolgreich
[ ] HSTS-Header in nginx.conf aktiviert (nach erstem stabilen Deploy)
[ ] Healthcheck: https://{ROTARY_DOMAIN}/health → "ok"
[ ] API-Test: https://{ROTARY_DOMAIN}/api/v1/stats → JSON
```

---

## Hinweis zu DSGVO / Impressum

Da Frontend B öffentlich ist (auch für nicht eingeloggte Besucher):

- **Impressum erforderlich** (§ 5 TMG) — in V12 „Über das Projekt" zu integrieren
- **Datenschutzhinweis erforderlich** — insbesondere für:
  - Nginx-Access-Logs (IP-Adressen)
  - `author_email_enc` (verschlüsselt gespeicherte E-Mail-Adressen)
- Empfehlung: Nginx-Logs auf 7 Tage Retention begrenzen:
  ```nginx
  access_log /var/log/nginx/access.log combined;
  # Log-Rotation in /etc/logrotate.d/nginx: rotate 7, daily
  ```
