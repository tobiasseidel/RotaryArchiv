# T3-nginx-config.md

> **Thread:** T3 Auth & Deployment  
> **Version:** 1.0 — 2026-05-02  
> **Abhängigkeiten:** project-brief_v03.md, T2-migrations-plan.md  
> **Input für:** T6 Coding, T5 Frontend/Design

---

## Überblick

Nginx fungiert als einziger öffentlicher Eintrittspunkt. Alle anderen Dienste
sind ausschließlich im internen Docker-Netz erreichbar.

```
Internet
   │
   ▼
[Nginx :80/:443]          ← einziger exposed Port
   │
   ├──▶ /                 → Frontend B (statische Dateien oder Node-Container)
   ├──▶ /api/             → Backend B  (intern: backend_b:8085)
   │
   └──▶ KEIN Zugriff auf Backend A, PostgreSQL, Fuseki von außen
```

---

## Nginx-Konfiguration

### Dateistruktur auf der NAS

```
/volume1/docker/rotary-archiv/
├── nginx/
│   ├── nginx.conf               ← Hauptkonfiguration
│   └── conf.d/
│       └── rotary.conf          ← Virtueller Host
├── docker-compose.yml
└── .env
```

### nginx.conf (Basis)

```nginx
worker_processes auto;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout 65;

    # Sicherheits-Header (global)
    add_header X-Content-Type-Options  "nosniff"         always;
    add_header X-Frame-Options         "SAMEORIGIN"      always;
    add_header Referrer-Policy         "strict-origin"   always;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log  /var/log/nginx/error.log warn;

    include /etc/nginx/conf.d/*.conf;
}
```

### conf.d/rotary.conf — HTTP→HTTPS-Redirect

```nginx
server {
    listen 80;
    server_name ${ROTARY_DOMAIN};          # z.B. archiv.rotary-dresden.de

    # ACME-Challenge für Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```

### conf.d/rotary.conf — HTTPS-Server

```nginx
server {
    listen 443 ssl http2;
    server_name ${ROTARY_DOMAIN};

    # TLS-Zertifikate (Let's Encrypt via Certbot oder lokales Zertifikat)
    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # HSTS (nach erstem erfolgreichen Deploy aktivieren)
    # add_header Strict-Transport-Security "max-age=31536000" always;

    # ─────────────────────────────────────────────────
    # Frontend B — statische Dateien
    # ─────────────────────────────────────────────────
    location / {
        # Option A: Statische Dateien direkt aus Volume
        root /var/www/rotary-frontend;
        index index.html;
        try_files $uri $uri/ /index.html;   # SPA-Fallback

        # Cache für Assets mit Hash im Dateinamen
        location ~* \.(js|css|woff2|png|svg|ico)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # ─────────────────────────────────────────────────
    # Backend B — API-Proxy
    # ─────────────────────────────────────────────────
    location /api/ {
        proxy_pass         http://backend_b:${BACKEND_B_PORT}/api/;
        proxy_http_version 1.1;

        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;

        # Timeouts (SPARQL-Abfragen können länger dauern)
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        # CORS — nur wenn Frontend und Backend auf verschiedenen Origins
        # (bei gleichem Nginx-Host nicht nötig)
        # add_header Access-Control-Allow-Origin "${ROTARY_DOMAIN}" always;
    }

    # ─────────────────────────────────────────────────
    # Explizite Sperren — kein externer Zugriff
    # ─────────────────────────────────────────────────
    location /admin/ {
        deny all;
        return 404;
    }

    # Gesundheitscheck-Endpunkt (intern für Portainer/Monitoring)
    location /health {
        access_log off;
        return 200 "ok";
        add_header Content-Type text/plain;
    }
}
```

---

## Entscheidungen & Begründungen

| Entscheidung | Gewählt | Begründung |
|---|---|---|
| TLS-Terminierung | Bei Nginx | Intern HTTP — kein Overhead durch doppelte TLS |
| SPA-Routing | `try_files … /index.html` | Notwendig für clientseitiges Routing (React/Vue) |
| API-Prefix | `/api/` | Klare Trennung, kein Path-Rewriting nötig |
| Backend A | Nicht exposed | Nur intern per Docker-Netz erreichbar |
| Fuseki | Nicht exposed | Nur intern — kein öffentlicher SPARQL-Endpunkt |
| HSTS | Auskommentiert | Erst nach stabilem TLS-Setup aktivieren |

---

## Domain-Optionen (offen bis T3-Abschluss)

| Szenario | Beispiel-Domain | Aufwand |
|---|---|---|
| Subdomain beim Club | `archiv.rotary-dresden.de` | DNS-Eintrag + Let's Encrypt |
| Eigene Domain | `rotaryarchiv-dresden.de` | Domain kaufen + DNS + Let's Encrypt |
| Lokaler Betrieb ohne Domain | `rotary.local` (nur intern) | Nur für interne Tests geeignet |
| DynDNS (NAS-IP nicht statisch) | z.B. Synology DDNS | Fallback wenn keine statische IP |

> **Empfehlung:** Subdomain beim Club (`archiv.rotary-dresden.de`) — minimaler
> Administrationsaufwand, glaubwürdige URL für Besucher.

---

## Certbot-Integration (Let's Encrypt)

Wenn die Domain öffentlich erreichbar ist, kann TLS vollständig automatisiert werden:

```yaml
# Ergänzung in docker-compose.yml (siehe T3-docker-compose.md)
certbot:
  image: certbot/certbot
  volumes:
    - ./nginx/certs:/etc/letsencrypt
    - ./certbot-webroot:/var/www/certbot
  entrypoint: >
    sh -c "certbot certonly --webroot -w /var/www/certbot
           -d ${ROTARY_DOMAIN} --email ${ADMIN_EMAIL}
           --agree-tos --non-interactive &&
           trap exit TERM; while :; do certbot renew; sleep 12h; done"
```

Erneuerung läuft automatisch alle 12 Stunden (Zertifikat wird 30 Tage
vor Ablauf erneuert). Nginx-Reload nach Erneuerung via:

```bash
docker exec rotary_nginx nginx -s reload
```

---

*Nächste Datei: T3-docker-compose.md*
