# Ravaan (روان) — Release Checklist & Runbook

This runbook describes the mechanical step-by-step procedure for cutting and verifying a production release of Ravaan.

---

## 1. Pre-Release Quality Gates

Run all automated quality and stability checks locally:

```powershell
# 1. Linting & Formatting (must pass with 0 errors)
ruff check .

# 2. Complete Test Suite (100% tests must pass)
pytest

# 3. Prediction Accuracy & Latency Benchmark (Target: Top-3 > 80%, p95 < 15ms)
python -m ravan.cli bench

# 4. System Diagnostics & Win32 API Selftest (All 7 checks must PASS)
python -m ravan.cli selftest

# 5. Memory & Latency Soak Test (RSS < 150 MB, latency drift < 50ms)
python -m ravan.cli soak

# 6. Verify LOC constraint (< 400 lines per Python file)
python -c "
import os
violations = [os.path.join(r, f) for r, _, fs in os.walk('.') if not any(x in r for x in ('.git', '.venv', '__pycache__', 'dist')) for f in fs if f.endswith('.py') and len(open(os.path.join(r, f), encoding='utf-8').readlines()) >= 400]
assert not violations, f'LOC limit violated: {violations}'
print('All files < 400 LOC')
"
```

---

## 2. Version Bump

Update the version string across all required files:

- [x] `ravan/__init__.py` (`__version__ = "2.0.0"`)
- [x] `pyproject.toml` (`version = "2.0.0"`)
- [x] `installer/setup.iss` (`#define MyAppVersion "2.0.0"`)
- [x] `scripts/generate_hashes.py` (`default="2.0.0"`)

---

## 3. Documentation Updates

- [x] **`CHANGELOG.md`**:
  - Add `## [2.0.0] - 2026-10-19` header following Keep a Changelog.
  - Detail Added, Changed, Deprecated, Removed, Fixed, and Security items.
- [x] **`ROADMAP.md`**:
  - Move completed milestones to `## Completed (v2.0.0 Stable Release)`.
  - Update `## Post-1.0 Ideas` if priorities evolved.
- [x] **`README.md`**:
  - Update version badges, milestone table (M34–M42), and installation commands.
- [x] **`docs/RELEASE_NOTES_TEMPLATE.md`**:
  - Verify bilingual release summary template reflects new features.

---

## 4. Git Tag & Push

```powershell
# 1. Stage and commit release changes
git add ravan/__init__.py pyproject.toml installer/setup.iss scripts/generate_hashes.py CHANGELOG.md ROADMAP.md README.md docs/
git commit -m "chore(release): vX.Y.Z"

# 2. Create annotated tag
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# 3. Push commit and tag to origin
git push origin main
git push origin vX.Y.Z
```

---

## 5. CI / CD Pipeline Verification

Open GitHub Actions and monitor the automated release workflow (`.github/workflows/release.yml`):

- [ ] **Lint & Tests**: verify `ruff` and `pytest` jobs succeed on runner.
- [ ] **PyInstaller Build**: verify `Ravaan.exe` compiles cleanly.
- [ ] **Inno Setup Build**: verify `Ravaan-Setup-X.Y.Z.exe` is created.
- [ ] **Portable Packaging**: verify `Ravaan-X.Y.Z-portable.zip` is created.
- [ ] **Windows Smoke Test**: verify runner downloads artifact and runs `Ravaan.exe --check-updates --version`.
- [ ] **Checksum Generation**: verify `SHA256` table is rendered and appended to release notes.
- [ ] **GitHub Release**: verify release is published with both assets attached.

---

## 6. End-to-End Post-Release Verification

On a clean Windows machine or test environment:

1. **Installer Test**:
   - Download `Ravaan-Setup-X.Y.Z.exe`.
   - Run setup (verify non-admin install into `%LOCALAPPDATA%\Programs\Ravaan`).
   - Launch Ravaan from Start Menu.
2. **First-Run Wizard**:
   - Verify Onboarding Wizard displays correctly on clean profiles.
3. **In-App Updater Verification**:
   - Open Tray menu → Click **Check for updates…**.
   - Verify dialog reports: *"You are using the latest version (X.Y.Z). No updates available."*
4. **Deep Link Protocol**:
   - Run `ravan://settings` in Windows Run dialog (Win+R) or browser address bar.
   - Verify Settings window opens smoothly.
5. **Uninstall Verification**:
   - Uninstall via Windows Settings → Installed Apps.
   - Verify program files are removed, while `%APPDATA%\Ravan\` user data is safely preserved.

---

## 7. Announcement

- [ ] Pin the new release on the GitHub repository releases tab.
- [ ] Share bilingual release notes with users and community channels.
