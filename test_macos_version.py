#!/usr/bin/env python3
"""
Test script for macOS version parsing fix (Item 1.5)
This tests the version parsing logic in isolation
"""

def parse_version_old(version_string):
    """Old fragile float-based approach"""
    v = float('.'.join(version_string.split('.')[:2]))
    return v

def parse_version_new(version_string):
    """New robust tuple-based approach"""
    version_parts = version_string.split('.')[:2]
    try:
        major = int(version_parts[0]) if version_parts else 0
        minor = int(version_parts[1]) if len(version_parts) > 1 else 0
    except (ValueError, IndexError):
        # If version parsing fails, assume modern macOS
        major, minor = 11, 0
    return (major, minor)

def test_version_comparisons():
    """Test version comparison logic"""
    print("=" * 70)
    print("TEST 1: Version Comparison Logic")
    print("=" * 70)

    test_cases = [
        ("10.14.6", (10, 15), False, "dot.bash_profile"),
        ("10.15", (10, 15), True, "dot.zshrc"),
        ("10.15.7", (10, 15), True, "dot.zshrc"),
        ("11.0", (10, 15), True, "dot.zshrc"),
        ("11.6.1", (10, 15), True, "dot.zshrc"),
        ("12.0", (10, 15), True, "dot.zshrc"),
        ("13.0", (10, 15), True, "dot.zshrc"),
        ("14.0", (10, 15), True, "dot.zshrc"),
        ("15.0", (10, 15), True, "dot.zshrc"),
    ]

    all_passed = True
    for version, threshold, expected_result, expected_file in test_cases:
        parsed = parse_version_new(version)
        result = parsed >= threshold
        file_choice = "dot.zshrc" if result else "dot.bash_profile"

        status = "✅ PASS" if result == expected_result else "❌ FAIL"
        if result != expected_result:
            all_passed = False

        print(f"{version:12} → {parsed} >= {threshold} = {result:5} → {file_choice:18} {status}")

    print()
    return all_passed

def test_edge_cases():
    """Test edge cases and error handling"""
    print("=" * 70)
    print("TEST 2: Edge Cases")
    print("=" * 70)

    edge_cases = [
        ("", "Empty string"),
        ("11", "Single component"),
        ("garbage", "Non-numeric"),
        ("10.x.5", "Mixed numeric/non-numeric"),
        ("10.15.7.1", "Four components"),
    ]

    all_passed = True
    for version, description in edge_cases:
        try:
            parsed = parse_version_new(version)
            file_choice = "dot.zshrc" if parsed >= (10, 15) else "dot.bash_profile"
            print(f"{version:12} ({description:25}) → {parsed} → {file_choice:18} ✅ PASS")
        except Exception as e:
            print(f"{version:12} ({description:25}) → ERROR: {e} ❌ FAIL")
            all_passed = False

    print()
    return all_passed

def demonstrate_float_bug():
    """Demonstrate why float comparison is wrong"""
    print("=" * 70)
    print("TEST 3: Demonstrate Float Bug (Why Old Approach is Wrong)")
    print("=" * 70)

    # The critical bug case
    print("\nCritical Bug Example:")
    print("-" * 70)
    print("Comparing macOS 10.9 vs 10.10:")

    v1 = "10.9"
    v2 = "10.10"

    # Old approach
    old_v1 = parse_version_old(v1)
    old_v2 = parse_version_old(v2)
    print(f"\nOld approach (WRONG):")
    print(f"  float('{v1}')  = {old_v1}")
    print(f"  float('{v2}') = {old_v2}  ← Loses trailing zero!")
    print(f"  {old_v1} > {old_v2} = {old_v1 > old_v2}  ← ❌ WRONG! Says 10.9 > 10.10")

    # New approach
    new_v1 = parse_version_new(v1)
    new_v2 = parse_version_new(v2)
    print(f"\nNew approach (CORRECT):")
    print(f"  tuple('{v1}')  = {new_v1}")
    print(f"  tuple('{v2}') = {new_v2}")
    print(f"  {new_v1} > {new_v2} = {new_v1 > new_v2}  ← ✅ CORRECT! Says 10.9 < 10.10")

    print("\nAnother example - macOS 10.15 vs 11.0:")
    print("-" * 70)
    v3 = "10.15"
    v4 = "11.0"

    old_v3 = parse_version_old(v3)
    old_v4 = parse_version_old(v4)
    new_v3 = parse_version_new(v3)
    new_v4 = parse_version_new(v4)

    print(f"Old: {old_v3} < {old_v4} = {old_v3 < old_v4}  ← Happens to work")
    print(f"New: {new_v3} < {new_v4} = {new_v3 < new_v4}  ← Semantically correct")

    print()
    return new_v1 < new_v2  # Should be True

def test_backward_compatibility():
    """Verify common macOS versions still work correctly"""
    print("=" * 70)
    print("TEST 4: Backward Compatibility")
    print("=" * 70)

    macos_versions = [
        ("10.15.7", "Catalina", "dot.zshrc"),
        ("11.6.8", "Big Sur", "dot.zshrc"),
        ("12.6.5", "Monterey", "dot.zshrc"),
        ("13.5.2", "Ventura", "dot.zshrc"),
        ("14.2.1", "Sonoma", "dot.zshrc"),
        ("10.14.6", "Mojave", "dot.bash_profile"),
    ]

    all_passed = True
    for version, name, expected_file in macos_versions:
        parsed = parse_version_new(version)
        file_choice = "dot.zshrc" if parsed >= (10, 15) else "dot.bash_profile"
        status = "✅ PASS" if file_choice == expected_file else "❌ FAIL"

        if file_choice != expected_file:
            all_passed = False

        print(f"macOS {name:12} ({version:9}) → {file_choice:18} {status}")

    print()
    return all_passed

def main():
    print("\n" + "=" * 70)
    print("macOS Version Parsing Fix - Test Suite")
    print("Item 1.5: Fix macOS version parsing bug")
    print("=" * 70)
    print()

    test_results = []

    # Run all tests
    test_results.append(("Version Comparisons", test_version_comparisons()))
    test_results.append(("Edge Cases", test_edge_cases()))
    test_results.append(("Float Bug Demo", demonstrate_float_bug()))
    test_results.append(("Backward Compatibility", test_backward_compatibility()))

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    total = len(test_results)
    passed = sum(1 for _, result in test_results if result)

    for name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{name:30} {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! The fix is working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed!")
        return 1

if __name__ == "__main__":
    exit(main())
