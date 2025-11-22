# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Security Model

Hoppy Whisper is designed with privacy and security as core principles:

- **Offline-first:** All audio processing and transcription happens locally on your device
- **No cloud services:** No audio or transcription data is transmitted to external servers
- **Local storage only:** Settings and history are stored in your Windows user profile directory
- **Minimal permissions:** Only requires microphone, clipboard, and optional registry access

## Known Security Considerations

### 1. Audio Capture
- **Threat:** Malicious applications could attempt to capture audio while Hoppy Whisper is running
- **Mitigation:** Audio is only captured while the hotkey is held; no persistent recording
- **User control:** Windows microphone permission can be revoked at any time

### 2. Clipboard Access
- **Threat:** Clipboard contents could be read by other applications
- **Mitigation:** Hoppy Whisper only writes to clipboard (does not read); sensitive transcriptions should be manually cleared from clipboard history
- **User control:** Windows clipboard access permission can be revoked

### 3. Local Storage
- **Threat:** Transcription history and settings are stored unencrypted in user profile
- **Mitigation:** File system permissions restrict access to current Windows user
- **User control:** Enable Windows BitLocker or similar full-disk encryption for sensitive data; clear history regularly via app menu

### 4. Model Downloads
- **Threat:** Man-in-the-middle attacks during initial model download from Hugging Face
- **Mitigation:** HTTPS is used for all model downloads; models are cached locally after first download
- **User control:** Download models on trusted networks; verify executable integrity before first run

### 5. Global Hotkeys
- **Threat:** Hotkey conflicts with other applications could cause unexpected behavior
- **Mitigation:** Clear error messages if hotkey registration fails; hotkey is configurable
- **User control:** Choose unique hotkey combinations

## Reporting a Vulnerability

If you discover a security vulnerability in Hoppy Whisper, please report it responsibly:

### Where to Report

**GitHub Security Advisories:** Use the "Security" tab in the GitHub repository to privately report vulnerabilities.

Alternatively, open a private security advisory or contact the maintainers through the repository discussions.

### What to Include

1. **Description** of the vulnerability
2. **Steps to reproduce** the issue
3. **Potential impact** (what could an attacker do?)
4. **Affected versions** (if known)
5. **Proposed fix** (optional)
6. **Your contact information** for follow-up

### What to Expect

- **Initial response:** Within 48 hours (acknowledgment of receipt)
- **Status update:** Within 7 days (initial assessment)
- **Resolution timeline:** Depends on severity and complexity
  - **Critical:** Fix within 7-14 days
  - **High:** Fix within 30 days
  - **Medium/Low:** Fix in next regular release

### Responsible Disclosure

We kindly ask that you:

- **Do not** publicly disclose the vulnerability until a fix is available
- **Do not** exploit the vulnerability beyond demonstrating the issue
- **Give us reasonable time** to address the issue before public disclosure
- **Notify us** if you discover the vulnerability has been publicly disclosed elsewhere

In return, we commit to:

- **Acknowledge** your report promptly
- **Keep you informed** of our progress
- **Credit you** in release notes (if you wish) when the fix is published
- **Respond professionally** and respectfully

## Security Best Practices for Users

### During Installation

1. **Download only from official sources:**
   - GitHub Releases
   - Microsoft Store (when available)
2. **Verify file integrity:**
   - Check file hashes if provided
   - Verify digital signature (if signed)
3. **Scan with antivirus** before running (optional but recommended)

### During Use

1. **Keep Windows updated** for latest security patches
2. **Use strong disk encryption** (BitLocker) if transcribing sensitive content
3. **Clear transcription history** regularly via History Palette → Clear All
4. **Review permissions** in Windows Settings → Privacy
5. **Monitor microphone indicator** to ensure recording only happens when expected
6. **Avoid using on shared/public computers** with sensitive transcriptions

### For Developers

1. **Keep dependencies updated:**
   ```powershell
   poetry update
   ```
2. **Run security audits** on Python packages periodically
3. **Review pre-commit hooks** before committing code
4. **Test on clean VM** before releasing builds

## Third-Party Dependencies

Hoppy Whisper relies on several third-party libraries. Security vulnerabilities in dependencies are addressed through:

1. **Regular updates:** Dependencies are reviewed and updated quarterly
2. **Automated monitoring:** GitHub Dependabot alerts for known vulnerabilities
3. **Pinned versions:** `poetry.lock` ensures reproducible builds
4. **Vetted providers:** All dependencies are from trusted sources (PyPI, Hugging Face)

### Key Dependencies

- **onnxruntime-directml** - Microsoft (ONNX Runtime with DirectML)
- **sounddevice** - PortAudio wrapper (audio capture)
- **webrtcvad** - Google WebRTC VAD
- **onnx-asr** - Speech recognition models
- **huggingface-hub** - Model downloads

See `pyproject.toml` for full dependency list and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for license information.

## Security Updates

Security fixes are released as:

1. **Patch versions** (e.g., 0.1.1 → 0.1.2) for minor issues
2. **Minor versions** (e.g., 0.1.0 → 0.2.0) for significant issues requiring API changes
3. **Out-of-band releases** for critical vulnerabilities

Subscribe to GitHub releases to receive security patches.

## Scope

This security policy covers:

- ✅ The Hoppy Whisper application code (`src/app/`)
- ✅ Build and distribution scripts
- ✅ First-party dependencies
- ❌ Third-party libraries (report to upstream maintainers)
- ❌ Windows operating system (report to Microsoft)
- ❌ User system misconfigurations

## Questions?

For security-related questions that are not vulnerabilities:

- Open a GitHub Discussion (for general questions)
- Check the issue tracker for similar concerns

Thank you for helping keep Hoppy Whisper secure!
