# Secrets in production

Everything in `.env.example` is a placeholder — safe to commit, useless to an attacker.
In any real deployment, none of the actual values (`DATABASE_URL` with a real password,
`JWT_SECRET`, `S3_ACCESS_KEY_ID`/`S3_SECRET_ACCESS_KEY`) would live in a `.env` file
checked into git or baked into a Docker image. They would be held in a managed secret
store — e.g. GitHub Actions Environment secrets for CI, plus AWS Secrets Manager /
Cloudflare's Workers & Pages secrets / Doppler / Vault for the running services — and
injected into the container's environment at deploy time (as env vars or a mounted
secrets file) by the deploy step itself, never written to disk in the image or the repo
history. Rotation would happen at the secret store, not by editing a file, and the CI
`deploy` job in `.github/workflows/ci.yml` shows where that injection point would sit if
this were pointed at a real environment.
