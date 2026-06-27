# Security Policy

## Supported Versions

The `main` branch is the actively maintained version.

## Reporting a Vulnerability

Please report security issues privately through GitHub security advisories or by contacting the repository owner.

Do not include real secrets, database dumps, user documents, API keys, JWT secrets, or production `.env` files in public issues.

## Deployment Security Checklist

- Replace `JWT_SECRET` with a long random value before deployment.
- Keep `OPENAI_API_KEY` empty unless you intentionally enable paid OpenAI APIs.
- Restrict `CORS_ORIGINS` to your deployed frontend domain.
- Use MongoDB authentication, backups, and network restrictions in production.
- Keep uploaded files and model cache volumes on trusted storage.
- Run the model prefetch command on the server so user requests do not trigger surprise downloads.
- Review dependency updates from Dependabot before merging.
