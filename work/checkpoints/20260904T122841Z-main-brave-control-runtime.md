# Checkpoint: main-brave-control-runtime

- **Created:** 2026-09-04T12:28:41Z
- **Status:** needs_input
- **Agent:** supervisor
- **Next action:** Restore Computer Use runtime, then select the exact primary Brave window, inspect existing Vercel/Cloudflare sessions, and continue UA-0035 without using the agent debug profile.

## Summary

The prior Vercel login was opened in the agent debug Brave profile by mistake. Main Brave processes are present, but Computer Use/CUA cannot initialize and therefore cannot safely select the user's primary Brave window.

## Tasks

- `UA-0035`
- none

## Blockers and risks

- Computer Use runtime fails before app/window enumeration: failed to write kernel assets: The system cannot find the path specified (os error 3).
- none

## Resume instructions

Restore Computer Use runtime, then select the exact primary Brave window, inspect existing Vercel/Cloudflare sessions, and continue UA-0035 without using the agent debug profile.
