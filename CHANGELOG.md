# Changelog

## 1.1.0 (2026-07-05)

- Added result limiting:
  - `limit` top-N mode on `/search`.
  - `max_results` hard cap (default 100, max 500).
- Improved search performance by requesting 500 portal results per page.
- Added response metadata: `matches_found`, `returned_count`, `scanned_portal_pages`.

## 1.0.2 (2026-07-05)

- Fixed JWT auth: ISLI Core internal tokens do not include an `iss` claim, so the skill no longer requires one. It still verifies the signature and expiry.

## 1.0.1 (2026-07-05)

- Fixed Dockerfile base image tag: `v1.45.0-python3.12` does not exist on MCR; use `v1.45.0-jammy`.

## 1.0.0 (2026-07-05)

- Initial release.
- Search open consultations by keyword, category, procedure, location, buyer, publication date, and deadline.
- List recent open consultations.
- Retrieve full consultation details including reference, object, buyer, procedure, deadline, location, estimated amount, contact info, and documents.
- ISLI USR v2.0 compliant Dockerized FastAPI microservice with JWT auth.
