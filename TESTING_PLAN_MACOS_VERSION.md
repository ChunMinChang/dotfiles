# Testing Plan - macOS Version Parsing Fix

## Item 1.5: Fix macOS version parsing bug

**File**: `setup.py:133-137`
**Impact**: HIGH - Affects macOS 10.15+ (Catalina and newer)

---

## The Problem

### Current Code (FRAGILE):
```python
if platform.system() == 'Darwin':
    v, _, _ = platform.mac_ver()
    v = float('.'.join(v.split('.')[:2]))
    platform_files[platform.system()].append(
        'dot.zshrc' if v >= 10.15 else 'dot.bash_profile')
```

### Issues:
1. **Semantic incorrectness**: Using float for version comparison is wrong
   - Version "10.2" vs "10.15": float(10.2) < float(10.15) ✗ (numerically true but...)
   - Version "10.9" vs "10.10": float(10.9) > float(10.10) ✗ (10.9 > 10.1, WRONG!)

2. **Edge case failures**:
   - Empty version string → ValueError
   - Single component "11" → works but fragile
   - Non-numeric components → ValueError
   - Version with more than 2 dots like "10.15.7" → works (takes first 2) but confusing

3. **Maintenance issues**:
   - Unclear intent (why float?)
   - Will confuse future maintainers

---

## The Solution

### New Code (ROBUST):
```python
if platform.system() == 'Darwin':
    v, _, _ = platform.mac_ver()
    version_parts = v.split('.')[:2]
    try:
        major = int(version_parts[0]) if version_parts else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    except (ValueError, IndexError):
        # If version parsing fails, assume modern macOS (use zshrc)
        major, minor = 11, 0

    platform_files[platform.system()].append(
        'dot.zshrc' if (major, minor) >= (10, 15) else 'dot.bash_profile')
```

### Why This Is Better:
1. ✅ **Semantically correct**: Tuple comparison for versions
2. ✅ **Handles edge cases**: Empty strings, single components, non-numeric
3. ✅ **Clear intent**: Obvious we're comparing version tuples
4. ✅ **Safe fallback**: Assumes modern macOS on parse failure
5. ✅ **Maintainable**: Future developers will understand this

---

## Test Cases

### Test 1: Syntax Validation
**Command**: `python3 -m py_compile setup.py`
**Expected**: No syntax errors

### Test 2: Version Comparison Logic (Unit Test)
Test various version strings:

| Version String | Major | Minor | Tuple | >= (10,15)? | Expected File |
|----------------|-------|-------|-------|-------------|---------------|
| "10.14.6" | 10 | 14 | (10,14) | False | dot.bash_profile |
| "10.15" | 10 | 15 | (10,15) | True | dot.zshrc |
| "10.15.7" | 10 | 15 | (10,15) | True | dot.zshrc |
| "11.0" | 11 | 0 | (11,0) | True | dot.zshrc |
| "11.6.1" | 11 | 6 | (11,6) | True | dot.zshrc |
| "12.0" | 12 | 0 | (12,0) | True | dot.zshrc |
| "13.0" | 13 | 0 | (13,0) | True | dot.zshrc |
| "14.0" | 14 | 0 | (14,0) | True | dot.zshrc |

### Test 3: Edge Cases

| Version String | Major | Minor | Tuple | Result | Expected File |
|----------------|-------|-------|-------|--------|---------------|
| "" | 0 | 0 | (0,0) | False | dot.bash_profile |
| "11" | 11 | 0 | (11,0) | True | dot.zshrc |
| "garbage" | 11 | 0 | (11,0) | True (fallback) | dot.zshrc |
| "10.x.5" | 11 | 0 | (11,0) | True (fallback) | dot.zshrc |

### Test 4: Old Float Logic (Demonstrate the Bug)
Show why float comparison is wrong:

```python
# Old approach problems:
float("10.9") = 10.9
float("10.10") = 10.1  # LOSES trailing zero!
10.9 > 10.1 = True  # WRONG! 10.10 is newer than 10.9

# New approach:
(10, 9) vs (10, 10)
(10, 9) > (10, 10) = False  # CORRECT!
```

### Test 5: Integration Test on Linux
**Command**: `python3 setup.py` (on Linux, should skip Darwin logic)
**Expected**: Works normally, doesn't execute Darwin branch

### Test 6: Backward Compatibility
Verify that common version strings still work correctly:
- macOS Catalina (10.15.x) → dot.zshrc ✅
- macOS Big Sur (11.x) → dot.zshrc ✅
- macOS Monterey (12.x) → dot.zshrc ✅
- macOS Ventura (13.x) → dot.zshrc ✅
- macOS Sonoma (14.x) → dot.zshrc ✅

---

## Testing Methodology

Since we're on Linux, we'll:
1. **Unit test the version parsing logic** in isolation
2. **Mock platform.mac_ver()** to return various version strings
3. **Verify correct file selection** for each version
4. **Demonstrate the float bug** with specific examples
5. **Test edge cases** with malformed version strings

---

## Success Criteria

- ✅ Syntax validation passes
- ✅ All version comparison tests pass
- ✅ Edge cases handled gracefully (no crashes)
- ✅ Backward compatible with existing macOS versions
- ✅ Code is more readable and maintainable
- ✅ No breaking changes to function behavior

---

## Risk Assessment

**Risk Level**: LOW

**Rationale**:
1. Only affects macOS users (we're on Linux)
2. Logic is straightforward tuple comparison
3. Includes safe fallback for edge cases
4. Maintains same behavior for all common versions
5. More robust than previous implementation

**Testing Limitation**:
- Cannot test on actual macOS (we're on Linux)
- Will use mock testing to verify logic correctness
- Code review to ensure correctness
