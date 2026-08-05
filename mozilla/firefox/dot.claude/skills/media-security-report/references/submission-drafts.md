# Submission drafts

One template per channel. The skill fills one of these into
`REPORT_DIR/submission-draft.md` so the user has something to paste, and then
stops. **The skill never sends, files, or submits.**

Placeholders in `<angle brackets>` are filled from
`scripts/media_lib_facts.py` output and the report itself.

## email-plain

The mail is a readable summary that stands on its own; the attached report
carries the full trace. Lead with the mechanism, not with the severity.

````text
To: <intake address>
Subject: <library> <revision>: <vulnerability class> in <function>

Hi <project> developers,

We think we have found a <memory-safety / integer-overflow / …> bug in
<component> <how it was found>, and we have <a one-line fix / no fix yet>. The
attached report has the full code trace, <the sanitizer stacks> and the
build/run steps; here is the short version.

Problem

<One or two paragraphs of mechanism, naming the functions and what state is
mishandled. Then the manifestations:>

    a <n>-byte <read/write> at `<expression>` in `<function>()`
      (`<file>:<line>`), and
    <the second manifestation, with its sanitizer classification and
      `<file>:<line>`>

The trigger is <an API sequence / a command line>. <If no CLI reproduces it,
say so and how the input is carried instead: "No <tool> command line does this,
so the packets are embedded as base64 inside the attached tests and no sample
file is needed.">

Still present on master `<hash>` (verified <date>, <platform> / <compiler>). It
looks like it dates back to `<hash>` ("<commit subject>", <year>), which
<what that commit introduced>.

Suggested fix

In `<function>()`:

```c
     <context>
+    <the added line>
     <context>
```

Tests

The <n> test patches apply cleanly to master with `git am`, in order, and add
<n> <harness> targets. Unfixed, all <n> fail, in both a sanitized and a plain
build; with the fix applied, all <n> pass. <Call out any oracle that detects
without a sanitizer, and how.>

Attribution

    Reviewer: <name> <<email>>
    Finder: <who or what found it>
    AI usage: <what AI assisted with>. Every claim, source line, stack trace
      and reproduction step was verified by hand on the revisions above;
      nothing is reported on the strength of an AI-generated result alone.
    CVE: <identifier, or "none assigned at report time">

<Your organisation>'s ETA

<Your disclosure stance: whether a deadline is planned, a request for a rough
ETA, and that you would rather take the fix from upstream than carry a local
patch. Offer to follow up when you have one.>

Attachments

    <report>.md - full report
    01-test-<desc>.patch - <what it detects>
    0N-fix-<desc>.patch - the suggested fix

Happy to reshape the tests or the fix into whatever form suits you.

Thanks for taking a look,
<name>
````

Attach the input and the patches. No key is published for these addresses, so
assume the mail is readable in transit — say nothing in it you would not
eventually publish.

Fill every placeholder from the report and from what the user tells you. Do not
invent a name, an employer, a disclosure deadline, or an AI-usage statement:
ask.

## email-gpg

```text
To: information@libjpeg-turbo.org
Subject: libjpeg-turbo <version>: <vulnerability class> in <function>
(GPG-encrypted to D291 2829 1D60 993B 8CC8 5724 8475 77AB B633 DB01)

This report meets the project's definition of a security vulnerability:
  - Affected release: <version>, which is in the <Next-Gen|Active|Maintenance|
    Extended> support category (not EOL).
  - The reproducer uses the <libjpeg|TurboJPEG> API correctly and allocates
    sufficient output buffer space.
  - The failure is triggered by malformed image data through a public API
    function.

AI usage: <"No AI was used." | "AI was used for <what>, at <where>; every
result was checked by hand by <name>.">
Reported by a human: <name>.

<report body>
```

Fetch and verify the key before sending; encrypt to yourself as well.

## buganizer

```text
Component: <component id>          Template: Security report
Type: Vulnerability                Access: Limited Visibility (set by the template)
CC: <your own account>             <- do this BEFORE submitting

Title: <library> <version>: <vulnerability class> in <function>

<library> version (use `git describe` if building from source): <ref>

VULNERABILITY DETAILS
<what the issue is and what it gives an attacker>

VERSION
<library> <ref>; also tested on <latest ref>.
Operating System: <os and version>

REPRODUCTION CASE
<copy/paste command>. The input is attached directly (not zipped).
Expected on the affected revision: <failure>.

FOR CRASHES
Type of crash: <process/tab/tool>
Crash State: <symbolized frames with file:line>

CREDIT INFORMATION
Reporter credit: <name or alias>

AI usage: <whether and where; who verified by hand>
```

Confirm `Type` reads `Vulnerability` and `Access` reads `Limited Visibility`
before pressing Create. If the tracker has no Security template (libyuv), set
Type by hand after CC'ing yourself.

## gitlab-confidential

```text
Open: <project>/-/issues/new?issue[confidential]=true
      (or Plan > Work items > New item > Type: Issue)
CONFIRM VISUALLY that "Turn on confidentiality" is ticked before submitting.
You cannot make it confidential afterwards.

Title: <library> <ref>: <vulnerability class> in <function>

<report body>

## Test input

Attaching files to a confidential issue in a public project would make them
world-readable, so the input is inline below.

  base64 -d > input-<desc>.<ext> <<'EOF'
  <base64 payload>
  EOF
```

For dav1d, follow up with a short plaintext mail to `security@videolan.org`
containing a one-paragraph summary and the confidential item's URL — no
technical detail, no attachment.

## github-pvr

```text
Repository: <owner>/<repo> > Security > Report a vulnerability

Title: <vulnerability class> in <function> (<library> <version>)

Summary
  <what and why it matters>
Product / Tested version
  <library> <ref>
Details
  <analysis with revision-pinned source links>
PoC
  <complete reproduction instructions>
Impact
  <consequence>
Remediation
  <proposed fix>
Credit
  <names>
AI usage
  <whether and where; who verified by hand>

Optional structured fields (welcome here, unlike Bugzilla):
  Affected versions: <range>     Patched versions: <version>
  Severity / CVSS: <vector>      CWE: <id>
```

If the form has no upload control, do not paste a binary blob into the
description. Say: "A `<n>`-byte reproducer is available; I can supply it via a
temporary private fork or any channel you prefer."

## bugzilla-restricted

```text
File at: https://bugzilla.mozilla.org/enter_bug.cgi?product=<product>&component=<component>
Security row: tick the product's default security group (core-security for Core)
Keep ticked: "CC list members can always see this bug"
CC: <external maintainer, or nobody for components with no upstream>
Keywords: crash, testcase, csectype-<class>, sec-<rating>

Summary: <library>: <ASAN finding> [@<symbol>]

<report body — this IS the Bugzilla bug, so Firefox context is fine here.
For an upstream library keep it standalone anyway: describe the defect in the
library's own terms so the CC'd maintainer can act on it without Firefox
knowledge.>

Attachments: <input file>, <patches>
```

After filing, verify the access actually landed:

```sh
curl -s "https://bugzilla.mozilla.org/rest/bug/<id>?include_fields=is_cc_accessible,groups,cc"
```

Expect `is_cc_accessible: true`, the security group set, and the maintainer in
`cc`. If `is_cc_accessible` is false the CC grants nothing and sends no mail.

Then send the maintainer a contentless heads-up:

```text
To: <maintainer>
Subject: Security report filed for <library>

I've filed a confidential <library> bug on bugzilla.mozilla.org and CC'd your
account (<address>). Please log in to view it. I haven't included any detail in
this message deliberately.
```

Omit CVSS scores, CWE identifiers and severity keywords from the report body —
Mozilla asks reporters not to set them.
