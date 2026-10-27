# Zetaris: blocked setup plan

No Zetaris endpoint or credentials were configured in this session. Do not provision AWS under the current no-paid-infrastructure constraint.

## First resolve the machine/access blocker

Windows reports 7.41 GiB usable RAM and about 1.2 GiB available. Check **Task Manager > Performance > Memory** and **Settings > System > About** for installed RAM and hardware-reserved memory. Do not allocate nearly all usable RAM to Docker. If the expected 16 GB cannot be made available, use an already authorized, adequately provisioned host or ask the sponsor whether existing access is available. No such host is currently confirmed.

For a suitable Windows machine, the [official prerequisites](https://github.com/zetaris/getting-started/blob/main/docs/install/choose-install.md) recommend Docker Engine 25+, 4 CPUs, 8 GB allocated memory (preflight rejects below 6 GB), and at least 15 GB free disk.

## Manual installation path, not performed

1. Install WSL2 (`wsl --install` in an administrator terminal), reboot as prompted, then install Docker Desktop and enable WSL integration. Confirm Docker's daemon and Compose work inside WSL.
2. Register/sign in through [Zetaris Start Here](https://github.com/zetaris/getting-started/blob/main/START-HERE.md), review the terms, and obtain the Run locally bundle, matching `.env`, registry credentials, and applicable entitlement. The public repository is not the platform distribution.
3. Follow the [official local guide](https://github.com/zetaris/getting-started/blob/main/docs/install/updated_zetaris_installation_guide.md). Keep credentials private; preserve supplied image references. Use its small local configuration and leave optional profiles off.
4. In the extracted bundle directory inside WSL, follow registry authentication, then run `./preflight.sh`, `docker compose config --quiet`, `docker compose pull`, `docker compose up -d`, and `./verify.sh`. Resolve failures before continuing.
5. In the authenticated SQL Editor, execute statements from `sql/zetaris-smoke.sql` individually. Capture results only after checking for sensitive content. Expected `SELECT 1 AS one;` output is one row containing 1; this has NOT been observed here.

## Optional script access after an instance exists

Use [Zetaris's official HTTP helpers](https://github.com/zetaris/getting-started/blob/main/scripts/HOWTO.md), not an invented API. Configure `ZETARIS_BASE_URL` (UI origin), `ZETARIS_ORG_ID`, and either `ZETARIS_API_KEY` or `ZETARIS_USERNAME` plus `ZETARIS_PASSWORD`. `.env.example` lists those names. Supply them through your local process environment or the official checkout's ignored `.env.local`; do not put passwords into command-line arguments. The bundle `.env` is a separate file. No secret values are needed in chat.

After dependencies and local credentials are configured in the official checkout, the documented proposed command is:

```powershell
python scripts/query_zetaris.py "SELECT 1 AS one;"
```

That script is in Zetaris's repository, not LifelineTwin's scripts directory. This command is not yet run. Prefer SQL Editor for the first query because it avoids additional client setup. Use [sample discovery](https://github.com/zetaris/getting-started/blob/main/docs/connections/lightning-recipe-reference.md) before assuming NY_TAXI is present or accessible.
