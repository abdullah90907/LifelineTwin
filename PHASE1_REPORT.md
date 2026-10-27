# Phase 1: technical foundation and sponsor feasibility

Date: 2026-10-24, Asia/Karachi. Scope ends at foundation and real sponsor checks. Phase 1 sponsor verification remains incomplete because Zetaris is blocked. Phase 2 has not started.

## Initial workspace and machine

`D:\Projects\LIfelineTwin` was empty, including hidden files; no existing Git repository or AGENTS.md was present. No unrelated files were overwritten. Git was initialized without committing or configuring a remote.

| Item | Actual observation |
|---|---|
| OS | Windows 11, kernel 10.0.26300, AMD64; registry DisplayVersion 26H2 |
| OS identification caveat | Registry ProductName says Windows 10 Pro Education; Python reports Windows 11. Kernel/build and architecture are confirmed; edition is not independently verified. |
| Python | 3.14.4 at C:\Python314\python.exe |
| Node / npm | v24.15.0 / 11.12.1 |
| Git | 2.54.0.windows.1 |
| CPU | AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD; 12 logical processors |
| RAM | 7.41 GiB usable physical memory; 1.2 GiB available at inventory time |
| Free disk | C: 31.86 GiB; D: 39.51 GiB at inventory time |
| Docker | Executable not found on PATH; daemon/Compose unavailable to this workflow |
| WSL | Executable exists; `wsl --status` explicitly says WSL is not installed |
| NVIDIA | `nvidia-smi` not found; GPU hardware/driver presence not established and not needed here |
| Zetaris configuration | No ZETARIS_* environment names present; no bundle or endpoint in the empty workspace |

Evidence: [machine.json](evidence/machine.json), [wsl-status.txt](evidence/wsl-status.txt). Memory uses Windows GlobalMemoryStatusEx, not the initial failed CIM calculation. Initial CIM OS/CPU access was denied; the zeros produced by that failed probe were NOT valid resource readings. Read-only Python/Windows APIs provided the later measurements. A CPU registry probe also failed with a type-cast error; exact CPU marketing name is unconfirmed.

## Official resources inspected

- [Zetaris START-HERE](https://github.com/zetaris/getting-started/blob/main/START-HERE.md), its install choice, local install, connection, sample SQL, and HTTP-helper pages linked in [setup notes](docs/zetaris-setup.md).
- [Meterless repository](https://github.com/Meterless/Meterless), root instructions, [World Model](https://github.com/Meterless/Meterless/tree/main/engines/world-model), its AGENTS.md, reference README, package/lock files, implementation source, smoke tests, and conformance runner.
- Meterless checked-out commit: `1742dec56a66e58eef9dda2d2b865823758ca8cd`; recorded in [meterless-commit.txt](evidence/meterless-commit.txt). No tracked upstream changes (`git diff --exit-code` succeeded).

## Zetaris result: BLOCKED, not tested

No SQL request was sent. There is no query result or server SQL error to claim. The actual prerequisite output was:

```text
docker: The term 'docker' is not recognized as a name of a cmdlet,
function, script file, or executable program.
The Windows Subsystem for Linux is not installed.
```

The shortest safe route is access to an existing authorized Zetaris instance, if available, then its SQL Editor. Otherwise resolve RAM, install WSL2/Docker on an adequate machine, and obtain the official account-issued distribution. Current usable RAM is too tight for a safe local allocation. We did not install Docker, create an account, download platform images, or provision cloud resources. Sponsor access/licensing is a manual prerequisite, not a public GitHub clone.

Prepared query: `SELECT 1 AS one;`. Additional sample-discovery statements are in [zetaris-smoke.sql](sql/zetaris-smoke.sql). All are marked proposed, not executed. Running those statements in SQLite, DuckDB, or a local Spark session would not prove Zetaris integration and was not attempted.

## Meterless result: reference works in process; restart limitation found

The real upstream WorldModel reference was imported, not rewritten or mocked. It runs TypeScript locally without a model, GPU, API credentials, or Docker. Installed 56 locked development packages with `npm ci`; no runtime dependency or model was added. This is the official reference, not the Nightshift application or a production hosted service.

| Executed check | Result | Evidence |
|---|---|---|
| Official smoke suite, one worker | PASS: 10/10, exit 0 | [meterless-tests.txt](evidence/meterless-tests.txt) |
| Official conformance runner | PASS: 8/8, exit 0 | [meterless-conformance.txt](evidence/meterless-conformance.txt) |
| Official idempotency script | PASS: second ingest processed 0, skipped 3, empty diff, exit 0 | [meterless-idempotency.txt](evidence/meterless-idempotency.txt) |
| LifelineTwin synthetic road check | PASS, exit 0 | [meterless-road.txt](evidence/meterless-road.txt) |
| Extra JSON-store reopen check | FAIL, exit 1: expected restricted, got undefined | [meterless-reopen.txt](evidence/meterless-reopen.txt) |

Actual road operations, using documented/source-confirmed methods:

1. `upsertEntity` creates external identity `road:synthetic:R001`.
2. `assertFact` records `status=closed` at `2026-10-24T08:00:00.000Z`.
3. `assertFact` records `status=restricted` at `2026-10-24T09:00:00.000Z` under `most-recent-wins`.
4. `view('graph').entity(id)` returns the current `restricted` status.
5. `view('facts').about(id)` returns both assertions; the old fact points to the winner through `supersededBy`. The winner's provenance identifies `road-update-002`, `synthetic-test`, and the later timestamp.
6. Repeating the second fact appends zero events. `audit()` returns the entity write and both fact writes.

Synthetic facts are test inputs only. Confidence 1 is a fixture value, not a calibrated claim about real roads. Times above are explicit UTC fixture times, not execution timestamps.

The original road check included reopening the persisted namespace and failed after all in-process assertions passed. The final script separates the successful core check from an optional `--check-reopen` diagnostic, which still fails visibly. No failing assertion was silently relaxed and no upstream repair was made.

Source inspection explains the failure: `assertFact` updates projected entity attributes during live writes, while EventStore's replay fold records facts without rebuilding that projection. Persisted files and provenance are present, but restart restoration of the current status is not confirmed. The failing check stops at the missing status; later reopen assertions are not claimed to have run. This limitation must be resolved with a regression-tested upstream correction or explicit adapter before production durability is claimed. That follow-up is not implemented in Phase 1.

## Commands and execution notes

Successfully executed from the project root unless otherwise stated:

```powershell
python --version
node --version
npm --version
git --version
py --list-paths
git clone --depth 1 --filter=blob:none --sparse https://github.com/Meterless/Meterless.git vendor/Meterless
git -C vendor/Meterless sparse-checkout set engines/world-model
git -C vendor/Meterless rev-parse HEAD
git -C vendor/Meterless diff --exit-code
git init
python scripts/inspect-machine.py
npm run test:road
```

Successfully executed inside `vendor/Meterless/engines/world-model/reference`:

```powershell
npm ci --no-audit --no-fund
npm test -- --maxWorkers=1
node node_modules/tsx/dist/cli.mjs ../conformance/runner.ts
npm run idempotency-check
```

Logs were captured with PowerShell `2>&1 | Tee-Object <evidence-path>` and test exit codes propagated. The npm install log is [meterless-install.txt](evidence/meterless-install.txt).

Initial restricted-shell clone failed to connect to GitHub port 443; the approved network execution succeeded. Restricted test attempts encountered evidence-file access denial and Node `uv_os_get_passwd returned ENOMEM`; approved execution outside that sandbox ran the same tools successfully. These sandbox errors are not treated as engine failures or evidence that physical RAM was exhausted. The file-access failures sometimes produced shell exit 0 despite no captured test run; only later explicit test output counts as success.

Failed/blocked commands: initial CIM probes, `docker --version`, `wsl --status`, initial sandbox clone/test attempts, and `npm run test:road -- --check-reopen`. The standalone idempotency `--mutate` CLI was not run; mutation sensitivity was exercised by the conformance and smoke tests instead. Browser bundle builds and the operator UI were not run.

## What was created and what happens next

Created a Git foundation, README, this report, ignored credential/vendor rules, credential-name example, machine inventory script, real reference road test, proposed Zetaris SQL, setup notes, and actual verification logs/persisted synthetic events. No services were purchased or provisioned; no model, frontend, forecasting, mapping, or full agent was built.

User action is required before resuming Zetaris:

1. Check installed versus usable RAM in Windows and report the non-secret figures, or identify an already authorized host/instance. Do not install the full platform on the measured memory budget.
2. On an adequate local host, complete WSL2/Docker setup and Zetaris portal registration/download/entitlement as detailed in the setup notes. Keep the bundle's matching configuration together.
3. Supply access locally through the official environment variable names or private configuration, never through chat. Tell the assistant only that configuration is ready and the non-secret endpoint/local bundle location.
4. Resume Phase 1: run official preflight/verification and the actual SQL query, capture output, and address the Meterless persistence regression before claiming durable readiness.

Paused at the manual Zetaris prerequisites. Both mandatory integrations are not yet confirmed; Phase 2 remains out of scope.
