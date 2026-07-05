# ISLI Maroc Marchés Publics Scanner

An [ISLI AI](https://github.com/medelmouhajir/isli-skills-registry) **Universal Skill Runtime v2.0** microservice that searches and retrieves open public procurement announcements from the Moroccan national portal [https://www.marchespublics.gov.ma](https://www.marchespublics.gov.ma).

## What it does

- **Search consultations** by keyword, category, procedure, location, buyer, publication date, and deadline.
- **List recent announcements** optionally filtered by category.
- **Get full details** of a single announcement, including deadlines, buyer, location, estimated amount, contact info, and document download links.

## Architecture

- Python 3.12 + FastAPI
- Playwright + Chromium for the JavaScript-driven portal pages
- BeautifulSoup for HTML parsing
- JWT auth via the `X-Internal-Auth` header as required by USR v2.0
- Dockerized for zero-code integration with ISLI Core

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/.well-known/isli-manifest` | ISLI manifest (from `isli-skill.yaml`) |
| POST | `/search` | Search open consultations |
| POST | `/details` | Get announcement details |
| POST | `/list_recent` | List recent announcements |

All `POST` endpoints require the `X-Internal-Auth` JWT header.

## Run locally

```bash
# 1. Configure the JWT secret used by ISLI Core
export JWT_SECRET="change-me"
export JWT_ISSUER="isli-core"

# 2. Build and run
docker-compose up --build

# 3. Test health
curl http://localhost:8000/health

# 4. Test search with a valid JWT
python - <<'PY'
import jwt, datetime, requests
token = jwt.encode(
    {"iss": "isli-core", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
    "change-me",
    algorithm="HS256",
)
res = requests.post(
    "http://localhost:8000/list_recent",
    headers={"X-Internal-Auth": token},
    json={"limit": 3},
)
print(res.status_code)
print(res.json())
PY
```

## Limitations

- **No public API** — the portal is scraped; selectors may need updates if the site redesigns.
- **Search is client-side filtered** — because the portal's search form uses JavaScript postbacks, the skill scans result pages and filters locally. Deeply paginated filtered results are limited by `max_pages_to_scan`.
- **Read-only** — the skill does not submit bids, log in, or interact with the cart.
- **v1 scope** — open consultations only; BDC award/result notices and monitoring alerts are planned for future versions.

## Submit to the ISLI skills registry

After publishing the skill repository, open a PR against `medelmouhajir/isli-skills-registry` adding an entry to `index.json`:

```json
{
  "id": "maroc-marches-publics-scanner",
  "name": "Maroc Marchés Publics Scanner",
  "description": "Search and retrieve open Moroccan public procurement announcements from marchespublics.gov.ma",
  "author": "ISLI Community",
  "git_url": "https://github.com/<owner>/<repo>.git",
  "tags": ["procurement", "morocco", "web", "scraper"]
}
```

## License

MIT
