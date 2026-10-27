# Zetaris local Windows setup report

Date: 2026-10-25 (Asia/Karachi).
Status: **Stopped awaiting an administrator WSL installation and restart. Success criteria are not yet met.**

## Prerequisites actually verified

- Windows 11 Pro, version 10.0.26300, AMD64: exceeds the documented WSL OS minimum and Docker Windows build minimum. Build number alone does not establish Docker support for a particular Windows servicing/Insider channel.
- Intel Core i7-10610U: 4 physical cores, 8 logical processors.
- Usable physical RAM: 15.67 GiB; currently available: 3.38 GiB.
- Free disk: C: 41.16 GiB; D: 48.05 GiB. Both exceed Zetaris's 15 GB minimum before images/data.
- Active Windows hypervisor: true. `systeminfo` reports virtualization-based security running and an active hypervisor. Firmware virtualization/SLAT CIM flags are false under the active hypervisor; these flags are not treated as proof virtualization is disabled. WSL2 operation still needs verification after installation.
- Current process has **no administrator token**, verified outside the restricted execution sandbox. Tool sandbox escalation is not Windows UAC elevation.
- WSL reports it is not installed. Docker CLI is absent, and neither standard all-users nor per-user Docker Desktop executable exists at the documented paths.
- User `.wslconfig` does not exist. No resource configuration has been applied.

## Actual command outputs

### `wsl --status`

Exit code: 50

```text
The Windows Subsystem for Linux is not installed. You can install by running 'wsl.exe --install'.
For more information please visit https://aka.ms/wslinstall

```

### `wsl --list --verbose`

Exit code: 1

```text
The Windows Subsystem for Linux is not installed. You can install by running 'wsl.exe --install'.
For more information please visit https://aka.ms/wslinstall

```

### `docker --version`

Not executed: executable not found. Actual process launch error:

```text
[WinError 2] The system cannot find the file specified
```

### `docker compose version`

Not executed: executable not found. Actual process launch error:

```text
[WinError 2] The system cannot find the file specified
```

### `docker info`

Not executed: executable not found. Actual process launch error:

```text
[WinError 2] The system cannot find the file specified
```

## Exact next action — administrator and restart required

Microsoft instructs opening PowerShell as administrator for initial WSL installation. In accordance with the user's explicit stop condition, no installer or UAC request was launched from this session.

1. Save open work.
2. Right-click Start, select **Terminal (Admin)** (or search PowerShell and select **Run as administrator**), then accept the UAC prompt.
3. Run:

```powershell
wsl --install -d Ubuntu
```

4. When installation completes, restart Windows. Do not interrupt installation to restart early.
5. After restart, open Ubuntu from Start and finish its first-run setup if prompted: create a Linux username and password. Keep the password private; no characters appearing while typing a Linux password is normal.
6. Return to this chat and confirm completion. If installation fails, return the exact error instead of repeating installation or removing anything.

## Remaining authorized work after that boundary

Not yet performed: install official Docker Desktop for Windows x86_64 with the WSL2 backend; complete any manual first-launch setup; check all five requested commands again; verify Linux backend and Docker Compose; apply and verify resources. No Docker installer has been downloaded or executed yet because the administrator/restart boundary comes first.

Planned Microsoft-supported global WSL2 resource settings in `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=8GB
processors=4
```

These settings are a shared WSL2 VM memory cap and virtual CPU count, not a reservation or proof of Docker capacity. Preserve any configuration present at continuation. Apply settings only at the appropriate stage; restarting WSL stops running distributions, so coordinate with any running work. Docker daemon `docker info` must subsequently confirm 4 CPUs and available memory consistent with the 8 GB WSL cap; small kernel overhead is expected. Current low free host RAM means other applications may need to be closed before allocating resources. No resource settings or shutdown commands were issued now.

Zetaris recommends 8 GB available to Docker, 4 CPUs, Docker Engine 25+, and 15 GB free disk; its preflight rejects below 6 GB. Docker/WSL memory availability remains unverified.

## Official sources consulted

- [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install): Administrator PowerShell, installation command, restart, and first-run distribution setup.
- [Microsoft WSL resource configuration](https://learn.microsoft.com/windows/wsl/wsl-config): `.wslconfig` memory/processors settings.
- [Docker Desktop Windows installation](https://docs.docker.com/desktop/setup/install/windows-install/): official installer, WSL2 backend and prerequisites.
- [Docker WSL2 backend](https://docs.docker.com/desktop/features/wsl/).
- [Zetaris local prerequisites](https://github.com/zetaris/getting-started/blob/main/docs/install/choose-install.md).

## Preservation and evidence

No application code changed. No Docker data, distributions, project files, or existing evidence deleted. No Zetaris installation/startup, AWS, paid service, commit, or push. Only the setup report and new diagnostic evidence were written.

Evidence directory: `evidence\zetaris-setup-20261025-191005` — `inventory.json`, `virtualization.txt`, and `commands.json`. Previous migration evidence is retained.
