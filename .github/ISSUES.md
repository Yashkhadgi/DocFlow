# GitHub Issues To Create

## Lead

- [ ] L1: Create repo structure and placeholder files
- [ ] L2: Commit frozen contracts and fixtures
- [ ] L3: Add docker-compose local stack
- [ ] L4: Configure GitHub branch protection, CODEOWNERS, PR template, issues, and project board
- [ ] L5: Announce contract freeze
- [ ] L6: Create deployment and service accounts

## Person A: Backend + Infra

- [ ] A1: Project skeleton and database
- [ ] A2: Auth
- [ ] A3: Storage service and upload endpoint
- [ ] A4: Celery worker and job lifecycle
- [ ] A5: Retries, backoff, failure handling
- [ ] A6: Read/review endpoints
- [ ] A7: Export endpoint
- [ ] A8: Backend deployment

## Person B: AI + Data

- [ ] B1: Sample pack
- [ ] B2: extract()
- [ ] B3: Prompt design and robustness
- [ ] B4: validate()
- [ ] B5: Review rules
- [ ] B6: find_business_duplicate()
- [ ] B7: Export helpers
- [ ] B8: Package and document extraction module

## Person C: Frontend + Story

- [ ] C1: Setup, routing, API client, mock layer
- [ ] C2: Login and upload
- [ ] C3: Dashboard
- [ ] C4: Split-screen review page
- [ ] C5: Export, polish, and states
- [ ] C6: Frontend deployment
- [ ] C7: Documentation and story assets
- [ ] C8: Demo preparation

## Integration

- [ ] I1: A + B swap stub for real extractor
- [ ] I2: A + C connect the real API
- [ ] I3: Full end-to-end live URL checklist

## Hardening

- [ ] H1: A file-security and retry pass
- [ ] H2: B live LLM evaluation and demo data tuning
- [ ] H3: C UI polish, docs, slides, demo rehearsal
- [ ] H4: Lead final regression and v1.0.0 tag
