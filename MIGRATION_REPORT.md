# LifelineTwin migration report

Date: 2026-10-25 (Asia/Karachi). Workspace: `D:\Projects 2026\LIfelineTwin`.

## Scope and preservation

Inspected README, all four phase reports, requirements, Python package and six test modules, cached geographic/weather data, prior evidence, Meterless reference, and Zetaris notes. No project recreation, geographic acquisition, application implementation, Zetaris installation/startup, commits, or pushes performed. The original `.venv` is preserved; it targets missing `C:\Python314\python.exe` and the former project location. New evidence is under `evidence/migration-20261025/`; new road checks create fresh `evidence/road-run-*` directories.

Git has an unborn `master` branch, no branch commits, and no branch reflog. Existing project files were already untracked at inspection. An internal Codex capture ref exists; this is not a migrated project branch history. No Git history was deleted or rewritten. Full prior development history cannot be confirmed from this copy.

## Environment

- Windows 11 Pro, build 10.0.26300, AMD64.
- Intel Core i7-10610U: 4 physical cores, 8 logical processors.
- RAM: 15.67 GiB usable; roughly 5.1–5.2 GiB available during inspection.
- Initial free disk: C: 40.72 GiB; D: 49.42 GiB (before dependency installation).
- Python: installed CPython 3.13.3 at `C:\Python313\python.exe`; new isolated environment `.venv-migration`.
- Node v20.20.2, npm 11.4.2, Git 2.49.0.windows.1.

Python 3.13 is the compatible locally installed choice: the saved IBM package explicitly requires `>=3.11,<3.14`, unlike the old Python 3.14 environment. PyTorch publishes Windows Python 3.13 CPU wheels. Phase 2 dependencies install unchanged from their lock file.

## Dependencies and compatibility

Original requirements files are preserved. `requirements-migration.txt` layers the Phase 2 lock and the copied IBM revision `9d0b839f997eb4918822a43036012ce8c277687c`, retaining saved Phase 3 versions where compatible. IBM metadata requires `torch>=2.10,<2.12` and `scikit-learn<1.8`, conflicting with original Phase 3 `torch==2.14.1+cpu` and `scikit-learn>=1.9.0`. Migration uses CPU torch 2.11.0+cpu and scikit-learn 1.7.2. No source changes or dependency bypasses are used.

Phase 2 installation: all 17 lock entries installed at their exact saved versions, including OSMnx 2.1.1, NetworkX 3.7, NumPy 2.5.4, pandas 3.1.0, GeoPandas 1.2.0.

Initial sandbox temporary-directory and network restrictions were resolved using a workspace temporary directory and authorized dependency installation. Git's Windows long-path checkout error was resolved with process-local `core.longpaths=true`; global Git settings were not changed. A PyPI timeout required a retry.

## Zetaris readiness

| Prerequisite | Observed result |
|---|---|
| WSL2 | Not installed: both `wsl --status` and `wsl --list --verbose` report WSL absent. |
| Docker Desktop / CLI | Docker command absent; standard Docker Desktop executable absent. No daemon or Compose verification possible. |
| CPU | Meets hardware recommendation: 4 physical cores / 8 logical CPUs. Docker allocation remains unconfigured. |
| Disk | Both C: and D: initially exceed 15 GB free. |
| Memory | 15.67 GiB usable hardware, but only about 5.2 GiB currently free; 8 GB Docker allocation has not been established. |
| Virtualization | `HypervisorPresent=true`; systeminfo confirms active hypervisor and running virtualization-based security. CIM firmware/SLAT flags return false under the active hypervisor; those flags alone do not establish disabled virtualization. WSL2 operational readiness is unverified. |
| Platform access | No configured Zetaris environment names; entitlement, bundle, registry access, and SQL remain unverified. |

Zetaris is **not ready to run**. Nothing was installed or started. Official prerequisites recommend Docker Engine 25+, Windows WSL2, 4 CPUs and 8 GB available to Docker (preflight minimum 6 GB), and at least 15 GB free disk: [Zetaris prerequisites](https://github.com/zetaris/getting-started/blob/main/docs/install/choose-install.md).

## Validation results

**Migration environment validated, with existing application limitations and Zetaris prerequisites outstanding.**

| Check | Actual result |
|---|---|
| Complete existing Python suite | **PASS: 51 tests, 174.882 seconds, zero failures/errors/skips; exit 0.** |
| Dependency consistency | PASS: `pip check` reports no broken requirements. |
| Source compilation | PASS: compileall of package, tests, and scripts; exit 0. |
| Geographic cache | PASS: all four manifest SHA-256 checksums match; 1,060 nodes, 2,331 directed edges, 9 origins, 27 facility records. No geographic download. |
| Phase 2 / 2.5 reproducibility | PASS: closures, per-origin changes, and restoration rankings exactly equal saved evidence; HTTP blocked during this comparison. |
| Phase 2 CLI | PASS, exit 0, new output path used. |
| Phase 2.5 CLI | **FAIL, exit 1**: existing quoted dictionary key causes `KeyError: '\"\'area\'\"'` during console printing. Analysis and new JSON output complete before this error. Library tests and reproducibility pass; original source left unchanged. |
| Live Open-Meteo | PASS: direct forecast API call returned 72 hourly records and all six expected variables. Cache parsing/fallback tests also pass. |
| Genuine pretrained TTM | PASS: official `ibm-granite/granite-timeseries-ttm-r1` snapshot `f04bebdd4c13475b006ce72672e74c9dc28871dc`; 805,280 parameters, actual parameter device CPU, 512-hour input, 96 finite hourly predictions; measured forward pass 16.71 ms. |
| Original files | PASS: all 64 baseline-hashed source/data/evidence/support files unchanged after verification; final preservation check also saved. |

Direct TTM verification used the original 888-hour weather cache. First five predictions: `8.7659320831, 8.8197669983, 8.7070779800, 8.5805912018, 8.4236135483`. Model weights are cached under `.runtime/huggingface`, not in the old laptop environment. No training performed. This confirms inference execution, not forecast accuracy: the old Phase 3 report labels a window extending to October 30 as historical ground truth despite its October 25 report date; forecast API output can include future forecasts. Those existing accuracy claims were not re-certified by this migration.

The earlier geography-only attempt before torch installation produced two import errors, because package initialization imports forecasting. Those preliminary logs are retained; the final complete suite above supersedes them. Installation retry logs are also retained, rather than overwritten.

Final package inventory: `evidence/migration-20261025/pip-freeze.txt`. Reproducible resolved requirements: `requirements-migration-lock.txt`. Installation used the PyTorch CPU index in addition to public PyPI. New same-day weather cache files created by the unmodified suite do not replace the October 24 originals.

Meterless: official smoke suite 10/10 PASS, conformance 8/8 PASS, idempotency PASS, road-update/provenance PASS. Existing optional persistence-reopen diagnostic FAILS (`undefined` versus expected `restricted`), reproducing the Phase 1 limitation.

## Sources

- [IBM project dependency metadata](https://github.com/ibm-granite/granite-tsfm/blob/main/pyproject.toml); exact constraints also inspected in the copied package METADATA.
- [PyTorch Windows installation support](https://pytorch.org/get-started/locally/).


## Remaining blockers and limitations

1. Zetaris cannot run until WSL2 and Docker Desktop are separately installed/configured, Docker memory/CPU allocations are verified, and platform access is obtained. No such installation was attempted.
2. Existing Meterless persistence-reopen assertion still fails; in-process operation passes.
3. Existing Phase 2.5 CLI console formatting fails despite valid analysis/JSON; source repair is outside this environment-only migration and was not performed.
4. Prior project branch history is absent from this copy; recover it from the original laptop or an existing remote if required. No new repository or commits were created.
5. Windows Hugging Face symlinks are unavailable; the cache uses regular files successfully. No administrator or Developer Mode setting was changed.

## Run on this laptop

From the project root in PowerShell:

```powershell
$env:HF_HOME = Join-Path (Get-Location) '.runtime/huggingface'
.\.venv-migration\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-migration\Scripts\python.exe -m lifelinetwin_geo analyze --output evidence/my-new-results.json
```

Choose a new output filename for each analysis to preserve previous results. The default CLI output paths target historical evidence. Optional activation: `.\.venv-migration\Scripts\Activate.ps1`; explicit executable paths avoid execution-policy changes. The old `.venv` remains untouched and unusable on this laptop. To recreate the migration environment, use Python 3.13 and `python -m pip install -r requirements-migration-lock.txt` in a fresh virtual environment.

Evidence: `full-tests.txt`, `full-tests-exit.txt`, `verification.json`, `pip-check.txt`, `pip-freeze.txt`, hardware inventory, CLI outputs, Meterless outputs, and installation logs in `evidence/migration-20261025/`.

Stopped after environment validation. No agent/frontend development, Zetaris startup, commit, or push.

Final disk free after setup: C:/ 40.52 GiB, D:/ 48.06 GiB.
