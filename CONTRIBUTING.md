# Contributing to NEXORA AI

1. Branch from `main` (feature/<topic>).
2. Run `cd backend && python -m pytest tests -q` - tests must pass.
3. Keep secrets out of the repo: use `.env` (gitignored) and `.env.example` placeholders only.
4. Update `README.md` (stage log) and the relevant `documentation/` file with any behavior change.
5. One feature per pull request, with a short description of what changed and how it was tested.
