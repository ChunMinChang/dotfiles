# Gecko Architecture Lookup Guide

This guide provides structured approaches for understanding Gecko architecture,
control flow, ownership, and subsystem interactions during root cause analysis.
Use this instead of depending on an external gecko-navigator agent.

## When to Use

Use these techniques when you need to answer:
- "How does X connect to Y?"
- "What owns this object's lifetime?"
- "What is the threading model for Z?"
- "How does an error propagate from A to B?"
- "What state machine governs this behavior?"

## Lookup Strategies

### 1. Symbol and Definition Search
```bash
# Find where a class/function is defined
searchfox-cli --define <ClassName>
searchfox-cli --id <symbol> --cpp -l 50

# Find callers of a function
searchfox-cli -q "callers:<FunctionName>" -l 30

# Find implementations of a virtual method
searchfox-cli --id <MethodName> --cpp -l 30
```

### 2. Header File Analysis
Read the class header to understand:
- **Inheritance hierarchy**: base classes, interfaces implemented
- **Ownership annotations**: `RefPtr<T>`, `UniquePtr<T>`, `MOZ_KNOWN_LIVE`, `MOZ_NON_OWNING_REF`
- **Threading annotations**: `MOZ_GUARDED_BY(mMutex)`, `NS_DECL_THREADSAFE_ISUPPORTS`
- **Member variables**: what state the class holds
- **Method signatures**: what's virtual, what's const, what's static

### 3. IPC Protocol Files
For cross-process communication, read the IPDL files:
```bash
searchfox-cli -q blob --path ipc/ipdl <ProtocolName>
searchfox-cli -q blob --path dom --path "*.ipdl" <keyword>
```
IPDL defines:
- Parent/Child actor pairs
- Message types (async, sync, intr)
- State machines for protocol transitions
- Managed actors (lifecycle tied to parent)

### 4. WebIDL Files
For JS-exposed interfaces:
```bash
searchfox-cli --id <InterfaceName> -p dom/webidl
```
WebIDL defines:
- What methods/attributes are exposed to JavaScript
- Which methods throw exceptions
- Pref-gated features (`[Pref="media.feature.enabled"]`)
- ChromeOnly interfaces (not web-exposed)

### 5. State Machine Analysis
Common in dom/media. Look for:
- Enum classes defining states (e.g., `enum class State { ... }`)
- Switch statements on state
- Transition functions (e.g., `SetState(newState)`, `OnStateChange()`)
- State diagrams in comments

Key media state machines:
- **MediaDecoderStateMachine (MDSM)**: controls decode/play/seek/shutdown
- **ExternalEngineStateMachine**: Windows Media Foundation Engine states
- **CDMProxy**: DRM lifecycle states
- **MediaFormatReader**: demuxing/decoding pipeline states

### 6. Git History Analysis
```bash
# Who wrote this code and why
git blame -L <start>,<end> <file>
git log --oneline --follow -S "<symbol>" -- <file> | head -10

# jj equivalents
jj annotate <file>
jj log -r 'ancestors(trunk())' -T builtin_log_oneline -s -- <file> | head -30
```

## Common Gecko Subsystem Patterns

### Media Pipeline
```
HTMLMediaElement
  → MediaDecoder (owns the pipeline)
    → MediaDecoderStateMachine (state management)
      → MediaFormatReader (demuxing)
        → PlatformDecoderModule (PDM) factory
          → Platform-specific decoder (FFmpeg, WMF, VDA, etc.)
```

### IPC Actor Pairs
```
Content Process          |  Parent/GPU Process
<Protocol>Child  ←IPC→  <Protocol>Parent
  (runs on main thread)     (runs on main/IO thread)
```
Common pairs: PMediaDecoderParams, PMFCDM, PMFMediaEngine, PRemoteDecoder

### Threading Model
- **Main thread**: DOM, script, UI events, most actor message handling
- **Media thread pool**: decode, demux, audio processing
- **Compositor thread**: rendering, layer transactions
- **GPU process**: hardware-accelerated decode, compositing
- **Utility process**: media decode sandboxing (newer)

Thread dispatch patterns:
```cpp
// Dispatch to main thread
NS_DispatchToMainThread(runnable);
// Dispatch to specific thread
mThread->Dispatch(runnable);
// AbstractThread (media task queues)
mAbstractMainThread->Dispatch(runnable);
```

### Lifecycle Patterns
- **RefCounted**: `NS_DECL_ISUPPORTS` / `NS_DECL_THREADSAFE_ISUPPORTS`
  - AddRef/Release, prevent raw pointers
- **Init/Shutdown**: many media objects have explicit `Init()` and `Shutdown()` methods
  - Shutdown may be async (returns a promise or callback)
  - Double-shutdown protection via state checks
- **MozPromise**: async result passing
  - `Then()` for success/failure callbacks
  - `Track()` for request tracking (cancel on shutdown)

### Error Propagation
- **nsresult**: C++ error codes (NS_OK, NS_ERROR_*, etc.)
- **MediaResult**: wraps nsresult + description string
- **MozPromise rejection**: async error propagation
- **IPC**: errors cross process boundaries via IPDL messages
- **HRESULT**: Windows-specific (MF, DXVA errors)

## Example Architecture Questions

Instead of asking a gecko-navigator agent, do these lookups directly:

**Q: "What owns MediaDecoder's lifetime?"**
→ Read `dom/media/MediaDecoder.h` header. Look for RefPtr usage.
→ `HTMLMediaElement` holds a `RefPtr<MediaDecoder>`.
→ Check `Shutdown()` for cleanup sequence.

**Q: "How does an error in the GPU process CDM reach the content process?"**
→ Find the IPDL protocol: `searchfox-cli -q blob --path "*.ipdl" CDM`
→ Read the actor pair: PMFCDM{Parent,Child}
→ Trace: error in GPU → `SendNotifyError()` IPC → `RecvNotifyError()` in content → promise rejection

**Q: "What is the threading model for MFMediaEngineParent?"**
→ Read `MFMediaEngineParent.h`, look for `MOZ_GUARDED_BY`, thread dispatch calls
→ Check which thread the actor runs on (IPC actors: background thread by default)
→ Look for `AssertOnManagerThread()` or similar assertions
