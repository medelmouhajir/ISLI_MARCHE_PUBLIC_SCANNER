# Changelog

## 1.0.1 (2026-07-05)

- Fixed Dockerfile base image tag: `v1.45.0-python3.12` does not exist on MCR; use `v1.45.0-jammy`.

## 1.0.0 (2026-07-05)

- Initial release.
- Search open consultations by keyword, category, procedure, location, buyer, publication date, and deadline.
- List recent open consultations.
- Retrieve full consultation details including reference, object, buyer, procedure, deadline, location, estimated amount, contact info, and documents.
- ISLI USR v2.0 compliant Dockerized FastAPI microservice with JWT auth.
