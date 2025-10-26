# Privacy Policy for Hoppy Whisper

**Last Updated:** October 26, 2025

## Overview

Hoppy Whisper ("the App") is a Windows desktop application that provides offline speech-to-text transcription. This Privacy Policy explains how we handle data when you use our application.

## Our Commitment to Privacy

**Hoppy Whisper is designed with privacy as a core principle.** All audio processing and transcription happens entirely on your local device. We do not collect, transmit, or store any personal data on external servers.

## Information We Do NOT Collect

- **Audio recordings** - Never uploaded, stored only temporarily in memory during transcription
- **Transcribed text** - Remains on your device only
- **Personal information** - No names, emails, phone numbers, or addresses
- **Usage analytics** - No tracking of how you use the app
- **Location data** - No access to or collection of location information
- **Unique device identifiers** - No tracking across devices
- **Telemetry data** - No crash reports or performance metrics sent to servers

## Information Stored Locally

The following data is stored exclusively on your device:

### 1. Application Settings
- **Location:** `%LOCALAPPDATA%\Hoppy Whisper\settings.json`
- **Content:** Your preferences (hotkey, paste delay, startup settings)
- **Purpose:** Maintain your custom configuration
- **Retention:** Until you uninstall the app or manually delete

### 2. Transcription History
- **Location:** `%LOCALAPPDATA%\Hoppy Whisper\history.db` (SQLite database)
- **Content:** Past transcriptions with timestamps
- **Purpose:** Allow you to search and reuse previous transcriptions
- **Retention:** 90 days by default (older entries automatically purged)
- **Control:** You can export or clear history at any time via the app menu

### 3. AI Models
- **Location:** `%LOCALAPPDATA%\Hoppy Whisper\models\`
- **Content:** ONNX Runtime speech recognition models
- **Purpose:** Enable offline transcription
- **Size:** ~500MB
- **Source:** Downloaded once from Hugging Face (public model repository)
- **Retention:** Cached permanently until app uninstall

## Permissions Required

Hoppy Whisper requires the following system permissions:

### 1. Microphone Access
- **Why:** To capture audio for transcription
- **When:** Only when you press and hold the hotkey
- **Scope:** Audio is processed in real-time and not permanently stored
- **Control:** Can be revoked via Windows Settings → Privacy → Microphone

### 2. Clipboard Access
- **Why:** To copy transcribed text and paste into active applications
- **When:** When you release the hotkey (transcription complete) and press again within the paste window
- **Scope:** Only writes text to clipboard, does not read existing clipboard content
- **Control:** Can be revoked via Windows Settings → Privacy → Clipboard

### 3. Registry Access (Optional)
- **Why:** To enable "Start with Windows" feature
- **When:** Only if you enable this option in settings
- **Scope:** Writes a startup registry key to `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run`
- **Control:** Can be disabled in app settings or Windows Task Manager → Startup

## Network Activity

Hoppy Whisper connects to the internet only for the following purposes:

### Initial Model Download
- **When:** First launch or when models are missing
- **Destination:** Hugging Face (huggingface.co)
- **Data Transmitted:** HTTP request for model files (no personal data)
- **Data Received:** ONNX model files (~500MB)
- **Frequency:** Once (models are cached locally)

**After initial download, the app works completely offline.**

### Future Updates (Optional)
- **When:** Only if you manually check for updates
- **Destination:** GitHub Releases or Microsoft Store (depending on installation method)
- **Data Transmitted:** Version check request (no personal data)
- **Frequency:** Only when explicitly triggered by user

## Third-Party Services

### Hugging Face (Model Hosting)
- **Purpose:** Hosts AI models for speech recognition
- **Data Shared:** None (models are downloaded anonymously via public URLs)
- **Privacy Policy:** https://huggingface.co/privacy

### ONNX Runtime (Local Inference)
- **Purpose:** Runs AI models locally on your device
- **Data Shared:** None (entirely offline processing)
- **Provider:** Microsoft (open-source project)

## Data Security

### Local Storage Security
- All local data is stored in your Windows user profile directory
- Access is restricted to your Windows user account
- No encryption is applied by default (relies on Windows file system permissions)
- If you need encryption, enable Windows BitLocker or similar full-disk encryption

### In-Memory Security
- Audio is processed in memory and immediately discarded after transcription
- No audio recordings are written to disk
- Transcribed text is cleared from memory after pasting (if paste occurs)

## Children's Privacy

Hoppy Whisper does not collect personal information from anyone, including children under 13. The app is suitable for all ages and does not require account creation or personal data entry.

## Data Retention and Deletion

### Transcription History
- **Default retention:** 90 days (automatically purged after this period)
- **Manual deletion:** 
  - Open History Palette (Win+Shift+Y)
  - Click "Clear All History"
  - Confirm deletion
- **Export before deletion:** Available in History Palette → Export to .txt or .json

### Complete Data Removal
To completely remove all data:

1. Uninstall Hoppy Whisper via Windows Settings → Apps
2. Manually delete: `%LOCALAPPDATA%\Hoppy Whisper\`
3. (Optional) Remove registry startup entry if enabled:
   - `HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run\Hoppy Whisper`

## Your Rights

You have complete control over your data:

- **Access:** All data is stored in readable formats (JSON, SQLite) in your user directory
- **Export:** Transcription history can be exported to .txt or .json
- **Delete:** Clear history or uninstall the app at any time
- **Portability:** Export files can be used with any text processing software
- **No account:** No sign-up or account creation, so no account-related data to manage

## Changes to This Policy

We may update this Privacy Policy to reflect changes in the app or legal requirements. Changes will be:

- Posted in the app's GitHub repository (README.md and PRIVACY_POLICY.md)
- Included in app updates
- Noted with a new "Last Updated" date at the top

Continued use of the app after changes constitutes acceptance of the updated policy.

## Open Source Transparency

Hoppy Whisper is open-source software. You can inspect the code to verify our privacy claims:

- **Source Code:** https://github.com/YOUR_USERNAME/Hoppy-Whisper (update with actual URL)
- **License:** MIT License
- **Audit:** All data handling code is publicly reviewable

## Contact Information

For privacy-related questions or concerns:

- **GitHub Issues:** https://github.com/YOUR_USERNAME/Hoppy-Whisper/issues (update with actual URL)
- **Email:** maintainers@hoppy.app
- **Response Time:** We aim to respond within 5 business days

## Compliance

### GDPR (European Users)
- No personal data is collected or processed
- No data is transmitted to servers outside your device
- No data controller or processor relationship exists
- Local storage only, controlled entirely by the user

### CCPA (California Users)
- No personal information is sold or shared
- No commercial use of user data
- Users have full control over local data storage

### Microsoft Store Policy Compliance
This app complies with Microsoft Store policies:
- No collection of personal information without consent
- Clear disclosure of permissions required
- Offline functionality after initial setup
- Transparent data handling practices

## Technical Details for Privacy Researchers

### Data Flow
1. **Audio Capture:** Microphone → sounddevice library → NumPy array (in-memory)
2. **Voice Activity Detection:** WebRTC VAD (local processing)
3. **Transcription:** ONNX Runtime with local models → text string (in-memory)
4. **History Storage:** SQLite database (local file)
5. **Clipboard:** pyperclip library → Windows clipboard API

### No Network Transmission
- Audio: Never transmitted (stays in memory)
- Text: Never transmitted (local clipboard only)
- Models: Downloaded once, cached forever
- Settings: Local JSON file only

### Verifiable Privacy Claims
- Network monitoring (e.g., Wireshark) will show no traffic except initial model download
- File system monitoring will confirm no data written outside `%LOCALAPPDATA%\Hoppy Whisper\`
- Process monitoring will confirm no subprocess communication with external services

## Summary

**Hoppy Whisper is a privacy-first application:**
- ✅ No data collection
- ✅ No cloud services
- ✅ No telemetry
- ✅ Offline operation (after initial setup)
- ✅ Local storage only
- ✅ Full user control
- ✅ Open-source and auditable

Your voice stays on your device. Your transcriptions stay on your device. Your privacy is protected.

---

**If you have questions about this policy or how Hoppy Whisper handles data, please open an issue on GitHub or contact us at maintainers@hoppy.app.**
