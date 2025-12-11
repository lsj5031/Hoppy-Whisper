# Remote Transcription Guide

Hoppy Whisper supports remote transcription via HTTP APIs, allowing you to use external ASR services instead of local ONNX models.

## Overview

When remote transcription is enabled:
- Audio is captured locally as usual
- The audio file (WAV format) is sent to your configured endpoint via HTTP POST
- The remote service transcribes the audio and returns the text
- The transcribed text is pasted into your active window

**Benefits:**
- No local model downloads (~500MB saved)
- Faster startup time (no ONNX Runtime initialization)
- Access to more powerful cloud-based models
- Lower local CPU/RAM usage

**Considerations:**
- Network latency affects transcription speed
- Audio data is sent to the remote service (privacy implications)
- Requires internet connection or accessible local server

## Configuration

Edit your settings file at `%LOCALAPPDATA%\Hoppy Whisper\settings.json`:

```json
{
  "remote_transcription_enabled": true,
  "remote_transcription_endpoint": "http://localhost:8000/transcribe",
  "remote_transcription_api_key": "your-api-key-here"
}
```

### Settings Reference

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `remote_transcription_enabled` | boolean | No | Enable/disable remote transcription (default: `false`) |
| `remote_transcription_endpoint` | string | Yes* | Full URL of the transcription endpoint |
| `remote_transcription_api_key` | string | No | Optional API key for authentication |

\* Required when `remote_transcription_enabled` is `true`

## API Requirements

Your remote endpoint must:

1. **Accept POST requests** with audio file as `multipart/form-data`
   - Field name: `audio`
   - Audio format: WAV (16kHz mono recommended, but most formats accepted)

2. **Return JSON** with transcription text in one of these formats:
   ```json
   {"text": "transcribed text"}
   ```
   or
   ```json
   {"transcription": "transcribed text"}
   ```
   or
   ```json
   {"result": "transcribed text"}
   ```
   or
   ```json
   {"results": [{"text": "transcribed text"}]}
   ```
   or
   ```json
   {"data": {"text": "transcribed text"}}
   ```

3. **Return HTTP 200** on success

4. **Optional: Support Bearer token authentication**
   - If `remote_transcription_api_key` is set, it will be sent as:
   - Header: `Authorization: Bearer your-api-key-here`

## Compatible Services

### GLM-ASR (Recommended for Self-Hosting)

[GLM-ASR Docker](https://github.com/lsj5031/glm-asr-docker) is a Docker-based ASR service that works seamlessly with Hoppy Whisper.

**Setup:**

1. Clone and start the GLM-ASR service:
   ```bash
   git clone https://github.com/lsj5031/glm-asr-docker.git
   cd glm-asr-docker
   docker-compose up -d
   ```

2. Configure Hoppy Whisper:
   ```json
   {
     "remote_transcription_enabled": true,
     "remote_transcription_endpoint": "http://localhost:8000/transcribe",
     "remote_transcription_api_key": ""
   }
   ```

### OpenAI Whisper API

**Configuration:**
```json
{
  "remote_transcription_enabled": true,
  "remote_transcription_endpoint": "https://api.openai.com/v1/audio/transcriptions",
  "remote_transcription_api_key": "sk-..."
}
```

**Note:** OpenAI's API may use a different request format. You may need to create a proxy service to adapt the format.

### Custom ASR Service

Create your own ASR endpoint:

```python
from fastapi import FastAPI, File, UploadFile
import whisper

app = FastAPI()
model = whisper.load_model("base")

@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    # Save uploaded file
    with open("temp.wav", "wb") as f:
        f.write(await audio.read())
    
    # Transcribe
    result = model.transcribe("temp.wav")
    
    # Return in compatible format
    return {"text": result["text"]}
```

Run with:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Configure Hoppy Whisper:
```json
{
  "remote_transcription_enabled": true,
  "remote_transcription_endpoint": "http://localhost:8000/transcribe",
  "remote_transcription_api_key": ""
}
```

## Testing Your Configuration

1. **Start your remote service** and verify it's accessible:
   ```bash
   curl http://localhost:8000/transcribe -X POST -F "audio=@test.wav"
   ```

2. **Update settings.json** with your endpoint configuration

3. **Restart Hoppy Whisper**

4. **Test recording**:
   - Press your hotkey (default: `Ctrl+Shift+;`)
   - Speak into your microphone
   - Release the hotkey
   - The tray icon should show "Transcribing..."
   - Transcribed text should be pasted into your active window

## Troubleshooting

### "Failed to connect to remote API"

**Possible causes:**
- Remote service is not running
- Incorrect endpoint URL
- Firewall blocking connection
- Network issues

**Solutions:**
- Verify the service is running: `curl http://localhost:8000/health`
- Check endpoint URL in settings.json
- Test connectivity: `curl http://localhost:8000/transcribe -X POST -F "audio=@test.wav"`

### "Remote API returned status 401/403"

**Possible causes:**
- Missing or incorrect API key
- Authentication format mismatch

**Solutions:**
- Verify `remote_transcription_api_key` is set correctly
- Check if the API expects a different auth format (e.g., `X-API-Key` header)
- Contact your API provider for authentication details

### "Could not extract transcription text from response"

**Possible causes:**
- API response format is not compatible
- API returned an error in non-standard format

**Solutions:**
- Check API response format: `curl -v http://localhost:8000/transcribe -X POST -F "audio=@test.wav"`
- Ensure response includes `text`, `transcription`, `result`, or `results` field
- Check Hoppy Whisper logs for the actual response received

### Slow transcription

**Possible causes:**
- Network latency
- Remote service is slow or overloaded
- Large audio files

**Solutions:**
- Use a local or nearby server to reduce latency
- Check remote service performance
- Reduce `transcribe_start_delay_ms` in settings if you want faster feedback

## Privacy Considerations

When using remote transcription:

1. **Audio data is transmitted** to the remote endpoint
2. **Ensure you trust the service provider** if using cloud services
3. **Use HTTPS endpoints** when transmitting over the internet
4. **Consider self-hosting** for maximum privacy (e.g., GLM-ASR Docker)
5. **Review the service's privacy policy** for cloud services

For completely private transcription, use the default local ONNX mode (`remote_transcription_enabled: false`).

## Switching Back to Local Transcription

To revert to local ONNX transcription:

1. Edit `settings.json`:
   ```json
   {
     "remote_transcription_enabled": false
   }
   ```

2. Restart Hoppy Whisper

The app will automatically download and use local models (~500MB) on first run.

## Advanced Configuration

### Custom Timeout

The default timeout is 30 seconds. To modify it, you'll need to customize the `RemoteTranscriber` initialization in the code.

### Custom Headers

To add custom headers (e.g., for API gateways), you'll need to extend the `RemoteTranscriber` class in `src/app/transcriber/remote.py`.

### Multiple Endpoints

To use different endpoints for different hotkeys or workflows, you can run multiple instances of Hoppy Whisper with different settings files using the `HOPPY_WHISPER_SETTINGS_PATH` environment variable.

## Example: Complete Setup with GLM-ASR

1. **Start GLM-ASR:**
   ```bash
   docker run -d -p 8000:8000 glm-asr
   ```

2. **Configure Hoppy Whisper:**
   ```json
   {
     "auto_paste": true,
     "hotkey_chord": "CTRL+SHIFT+;",
     "remote_transcription_enabled": true,
     "remote_transcription_endpoint": "http://localhost:8000/transcribe",
     "remote_transcription_api_key": ""
   }
   ```

3. **Restart Hoppy Whisper**

4. **Test:**
   - Press `Ctrl+Shift+;` and say "Hello world"
   - Release the hotkey
   - Text should be pasted automatically

## Support

For issues or questions:
- **Hoppy Whisper:** [GitHub Issues](https://github.com/lsj5031/Hoppy-Whisper/issues)
- **GLM-ASR:** [GitHub Issues](https://github.com/lsj5031/glm-asr-docker/issues)
