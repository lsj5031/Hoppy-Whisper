# Hoppy Whisper Codebase Analysis & Improvement Recommendations

## Overview
Hoppy Whisper is a robust Windows-native transcription tray app with good architectural separation. Analysis identified several areas for improved robustness and responsiveness.

---

## Critical Issues & Recommendations

### 1. **Thread Safety in History DAO (Medium Priority)**
**Location:** `src/app/history/dao.py:43`

**Issue:**
```python
self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
```
Using `check_same_thread=False` masks thread safety issues. The history is accessed from both:
- Main thread (menu, palette UI)
- Callback threads (transcription insert)
- Future background threads (search, export)

**Risk:** Database corruption under concurrent access.

**Recommendation:**
- Replace with proper thread-safe wrapper using `threading.Lock` 
- Add connection pooling for concurrent queries
- Use connection per-thread pattern with thread-local storage

**Implementation:**
```python
class HistoryDAO:
    def __init__(self, ...):
        self._db_path = db_path
        self._retention_days = retention_days
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()  # Add lock
    
    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Database not opened")
        return self._conn
    
    def insert(self, ...):
        with self._lock:
            if not self._conn:
                raise RuntimeError("Database not opened")
            # ... rest of insert logic
```

---

### 2. **Audio Callback Blocking (High Priority)**
**Location:** `src/app/__main__.py:407-440` and `src/app/audio/recorder.py:247-252`

**Issue:**
The audio callback calls `self._on_frames()` which triggers VAD processing. If VAD processing takes longer than audio chunk duration (~32ms), it blocks the PortAudio callback thread, causing:
- Audio buffer underruns
- Dropped audio frames
- Latency spikes

**Current Code:**
```python
def _audio_callback(self, indata, frames, time_info, status):
    # ...
    if self._on_frames is not None:
        self._on_frames(chunk)  # Blocks callback thread
```

**Recommendation:**
Use a lock-free queue to move VAD processing off the callback thread:

```python
from queue import Queue
import threading

class AudioRecorder:
    def __init__(self, ...):
        # ... existing code ...
        self._chunk_queue: Queue[np.ndarray] = Queue(maxsize=100)
        self._vad_thread: Optional[threading.Thread] = None
    
    def set_on_frames(self, callback):
        if callback and not self._vad_thread:
            self._vad_thread = threading.Thread(
                target=self._process_chunks,
                daemon=True
            )
            self._vad_thread.start()
        self._on_frames = callback
    
    def _process_chunks(self):
        """Process VAD on dedicated thread, non-blocking."""
        while self._recording:
            try:
                chunk = self._chunk_queue.get(timeout=0.1)
                if self._on_frames:
                    self._on_frames(chunk)
            except Queue.Empty:
                continue
    
    def _audio_callback(self, indata, frames, time_info, status):
        # ... buffer append logic ...
        try:
            self._chunk_queue.put_nowait(chunk)  # Non-blocking
        except:
            pass  # Drop frame if queue full
```

---

### 3. **Blocking UI Operations in Palette (Medium Priority)**
**Location:** `src/app/history/palette.py:158-175`

**Issue:**
Search queries are executed on the main (tkinter) thread, blocking UI during database operations:
```python
def _on_search_change(self, *_):
    query = self._search_var.get().strip()
    self._current_results = self._dao.search(query, limit=50)  # Blocks UI!
    self._update_listbox()
```

With many utterances, this causes noticeable lag.

**Recommendation:**
Move search to background thread with UI update on completion:

```python
def _on_search_change(self, *_):
    if not self._search_var:
        return
    query = self._search_var.get().strip()
    
    def _search_task():
        if not query:
            self._current_results = self._dao.get_recent(limit=50)
        else:
            self._current_results = self._dao.search(query, limit=50)
    
    def _on_complete():
        self._update_listbox()
        count = len(self._current_results)
        self._update_status(f"{count} result(s) found")
    
    threading.Thread(
        target=self._run_search,
        args=(query, _search_task, _on_complete),
        daemon=True
    ).start()
```

---

### 4. **Resource Cleanup Race Condition (Medium Priority)**
**Location:** `src/app/__main__.py:217-230`

**Issue:**
```python
def _handle_record_stop(self):
    self._audio_recorder.set_on_frames(None)  # Immediate detach
    # But _on_audio_chunk may still execute on PortAudio callback!
    self._vad = None
    self._vad_carry = np.array([], dtype=np.float32)
```

The callback can execute after detach, accessing freed/nulled resources.

**Recommendation:**
Add a flag for safe shutdown:

```python
def _handle_record_stop(self):
    self._vad_stop_requested = True
    self._audio_recorder.set_on_frames(None)
    # Wait for callback to exit
    time.sleep(0.05)  # One audio chunk period
    self._vad = None
    self._vad_carry = np.array([], dtype=np.float32)

def _on_audio_chunk(self, chunk):
    if self._vad_stop_requested:
        return  # Safe early exit
    # ... rest of processing
```

---

### 5. **Hard-coded Timeouts and Delays (Low-Medium Priority)**
**Location:** Multiple places:
- `__main__.py:257` - 0.8s transcription delay (arbitrary)
- `__main__.py:380` - 0.18s paste delay (magic number)
- `__main__.py:466` - 1.6s idle reset delay (inconsistent)

**Issue:**
Hard-coded delays are brittle and don't scale with actual latency.

**Recommendation:**
Convert to settings with sensible defaults:

```python
# settings.py
@dataclass
class AppSettings:
    # ... existing fields ...
    transcribe_start_delay_ms: float = 800  # ms to start transcription
    paste_predeplay_ms: float = 180  # ms before paste
    idle_reset_delay_ms: float = 1600  # ms to reset tray state

# Usage in __main__.py
self._transcribe_timer = threading.Timer(
    self._settings.transcribe_start_delay_ms / 1000,
    self._complete_transcription
)
```

---

### 6. **Exception Handling in Hotkey Callbacks (Medium Priority)**
**Location:** `src/app/hotkey/manager.py:250-257`

**Issue:**
Callback errors are silently swallowed:
```python
def _dispatch(self, handler):
    try:
        handler()
    except Exception as exc:
        try:
            self._callbacks.on_error(exc)
        except Exception:
            pass  # Silent failure
```

If `on_error` itself fails, the original error is lost.

**Recommendation:**
Log all errors before trying user callback:

```python
def _dispatch(self, handler):
    try:
        handler()
    except Exception as exc:
        LOGGER.exception("Callback error", exc_info=exc)
        try:
            self._callbacks.on_error(exc)
        except Exception as err:
            LOGGER.exception("Error callback also failed", exc_info=err)
```

---

### 7. **Database Connection Not Thread-Safe in Palette Export (Medium Priority)**
**Location:** `src/app/history/palette.py:269, 316`

**Issue:**
`export_all_to_dict()` fetches all data without pagination. With thousands of utterances:
- Massive memory spike
- UI freeze
- Potential OOM crash

**Recommendation:**
Paginate and stream export:

```python
def export_all_to_dict(self, batch_size: int = 1000) -> Iterator[dict]:
    """Yield utterances in batches to reduce memory usage."""
    offset = 0
    while True:
        cursor = self._conn.cursor()
        cursor.execute(
            """SELECT ... FROM utterances 
               ORDER BY created_utc DESC 
               LIMIT ? OFFSET ?""",
            (batch_size, offset)
        )
        rows = cursor.fetchall()
        if not rows:
            break
        for row in rows:
            yield {...}
        offset += batch_size

# In palette:
def _on_export_txt(self):
    with open(file_path, "w") as f:
        for utt_dict in self._dao.export_all_to_dict():
            # Write incrementally
```

---

### 8. **Unused Model Prefetch (Low Priority)**
**Location:** `src/app/__main__.py:666-679`

**Issue:**
Model prefetch runs on a daemon thread but:
- No way to know if it succeeds/fails
- Could be killed unexpectedly if main exits
- No progress feedback

**Recommendation:**
Make prefetch awaitable and block startup if offline mode needed:

```python
def _ensure_models_available(self, offline: bool = False) -> bool:
    """Ensure models are cached. Returns True if ready."""
    try:
        manager = get_model_manager()
        manager.ensure_models()
        return True
    except Exception as exc:
        if offline:
            LOGGER.error("Models not available in offline mode: %s", exc)
            return False
        LOGGER.debug("Model prefetch failed (non-blocking): %s", exc)
        return False
```

---

### 9. **Paste Delay Not Adaptive (Low Priority)**
**Location:** `src/app/__main__.py:370-403`

**Issue:**
Fixed 0.18s delay before paste doesn't account for:
- Slow app focus switches
- System load
- Network apps (slow text insertion)

**Recommendation:**
Make configurable and add retry logic:

```python
def _perform_paste(self, allow_ctrl_v: bool = True, retries: int = 3) -> None:
    delay = self._settings.paste_predelay_ms / 1000
    for attempt in range(retries):
        try:
            time.sleep(delay)
            # ... paste logic ...
            return
        except Exception as exc:
            if attempt < retries - 1:
                LOGGER.debug("Paste attempt %d failed, retrying", attempt + 1)
                delay *= 1.5  # Exponential backoff
            else:
                raise
```

---

### 10. **Transcriber Model Loading Not Isolated (Medium Priority)**
**Location:** `src/app/transcriber/hoppy.py:60-104`

**Issue:**
Model loading monkey-patches global onnxruntime state:
```python
ort.InferenceSession = _PatchedInferenceSession
ort._hoppy_patched = True
```

This is fragile and affects any other code using ORT.

**Recommendation:**
Create wrapper class instead of patching globals:

```python
class PatchedOrtSession:
    """Wrapper that auto-injects providers without global patching."""
    def __init__(self, providers, provider_options):
        self.providers = providers
        self.provider_options = provider_options
    
    def __call__(self, *args, **kwargs):
        if "providers" not in kwargs:
            kwargs["providers"] = self.providers
            kwargs["provider_options"] = self.provider_options
        import onnxruntime as ort
        return ort.InferenceSession(*args, **kwargs)
```

---

## Minor Issues

| Issue | Location | Impact | Fix |
|-------|----------|--------|-----|
| Double float32↔PCM16 conversion | `vad.py` & `buffer.py` | Slight perf loss | Create shared utility |
| No retry on transient network errors | `transcriber/hoppy.py` | Model download fails unnecessarily | Add exponential backoff retry |
| Tray notification errors ignored | `__main__.py:485` | Silent failures | Log details |
| No cleanup for temp files on crash | `hoppy.py:209-233` | Temp files accumulate | Use atexit handler |
| VAD state not reset between calls | `vad.py:87-91` | May affect subsequent recordings | Document or auto-reset |

---

## Performance Optimization Opportunities

1. **Audio Buffer Copy Reduction** (~2-5% CPU savings)
   - Currently: `indata.copy()` every callback
   - Could: Use pre-allocated circular buffer
   
2. **VAD Frame Conversion** (~3-8% CPU savings)
   - Currently: Float32→PCM16 for every frame in real-time
   - Could: Use SIMD-optimized float-to-int or reduce precision
   
3. **History Search Indexing**
   - FTS5 is good, but add frequency index on recent searches
   - Consider incremental search with early termination
   
4. **Hotkey Registration Caching**
   - Availability check happens on init, but not on update
   - Could cache results to speed up chord updates

---

## Summary

**Critical (Fix Before Release):**
- Thread safety in History DAO (#1)
- Audio callback blocking (#2)
- Resource cleanup race (#4)

**High (Fix Soon):**
- UI blocking in palette (#3)
- Logging for hidden errors (#6)

**Medium (Backlog):**
- Configuration for delays (#5)
- Memory-efficient export (#7)
- ORT patching (#10)

**Low (Nice-to-Have):**
- Model prefetch (#8)
- Paste retry logic (#9)
- Performance micro-optimizations

---

## Testing Recommendations

Add integration tests for:
- Concurrent history inserts + searches
- Audio callback under high-latency VAD
- Palette operations with 10k+ utterances
- Hotkey rapid press/release patterns
- Thread cleanup on app exit
