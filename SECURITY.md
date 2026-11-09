# Security policy

Clippy is a teaching project, but it is built to be reviewed like a real one.

## Reporting a vulnerability

Please do not open a public issue for a security problem. Email the maintainers (see the repository owner's profile) with what you found and how to reproduce it. You will get an answer within a few working days.

## What the project already does

- Accepts only absolute `http` and `https` URLs. `javascript:`, `data:` and relative URLs are rejected.
- Generates short codes with `secrets`, so they cannot be guessed from earlier ones.
- Keeps secrets out of the repository: `.env` files are ignored and `.env.example` contains no real values.
- Parameterised SQL only, never string concatenation.

## Known limits (by design, for teaching)

- No authentication or rate limiting. Put it behind Nginx or an API gateway and add them there.
- No TLS in the app. Terminate TLS in front of it.
- Anyone who can reach the API can create links.
