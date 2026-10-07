# 2026-10-07 — workflow bootstrap

## Purpose

Create a small Plume-native workflow using only the BOOSTED practices that transfer well to a Python engineering model.

## Starting point

Authoritative `main` before the sprint:

`ef0be9ac3dc3cb5bcba5f44dd5e37dd724d8b2b3`

The repository contained a runnable-looking Python screening prototype plus an archived PLUMES2.0 Windows distribution.

## Decisions

- Keep `PLUMES2.0-main/` immutable.
- GitHub Actions is the default mechanical closer for Python.
- Local Luna/Windows is reserved for reference evidence that requires `plumes2.0v1.exe` or another local-only dependency.
- Human owns modelling/product judgement and merge authority.
- Keep status/backlog/user input/gates durable in repository files.
- Defer package/file-layout refactoring until the PLUMES baseline is pinned.

## Environment probe

The ChatGPT Linux sandbox reported GNU Fortran 14.2.0. A minimal `.f90` program compiled and executed successfully, printing `PLUME_FORTRAN_SANDBOX_OK`.

The archived distribution does not contain FORTRAN source and the sandbox does not currently provide Wine, so this probe is capability evidence only.

## Retirement target

Bootstrap retires when the candidate is remotely identified, repository CI is green, and all remaining PLUMES/local evidence is routed to backlog/gates.
