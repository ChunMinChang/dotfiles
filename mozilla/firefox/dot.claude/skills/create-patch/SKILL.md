---
name: create-patch
command: /patch
description: Create a commit or patch file for Firefox contributions
---

You are helping create a commit or patch file for a Firefox bug fix or feature.

## Workflow

1. **Show context**: Display git status and recent commits to understand the context
   ```bash
   git status --short
   git log --oneline -5
   ```

2. **Ask all questions at once**: Use a SINGLE AskUserQuestion call to ask:
   - Bug number (infer from branch name if possible, e.g., "b2012791" → "2012791")
   - Commit or patch preference (recommend "Commit directly" - explain it's preferred for Mozilla workflow)
   - Which files to include (provide common presets + "Let me select specific files" option)
   - Commit message authorship: Who writes the title and summary?
     - "Claude generates it (Recommended)" - Claude analyzes and writes the message
     - "I'll write it myself" - User provides their own title and summary

   If user selects "Let me select specific files", use a SECOND AskUserQuestion with multiSelect.

3. **Analyze changes and context**:
   - Read the selected files and their diffs
   - Look at recent commits on this branch (`git log --oneline -3`) to understand:
     - The overall bug being fixed
     - What work has already been done
     - How this commit relates to previous commits
   - Understand what changed, why, and the technical details

4. **Generate or receive title and message**:

   **IMPORTANT**: Regardless of whether Claude generates the message or polishes user's draft,
   the final commit message MUST be as clear and concise as possible. Follow these principles:
   - Be direct and precise - avoid unnecessary words
   - Focus on what and why, not how
   - Use technical accuracy without verbosity
   - Every sentence should add value

   **If Claude generates it**:
   - Create a concise title (without "Bug XXXXX -" prefix, 50-72 chars)
   - Write a clear, focused summary that:
     - Describes what changed and why (be specific but brief)
     - Explains the purpose and goal (in 1-2 sentences if possible)
     - References previous commits if this is a follow-up
     - Includes only essential technical details
     - Removes any redundant or obvious information

   **If user writes it themselves**:
   - Ask the user to provide the title and summary (use text input or let them type it)
   - After receiving their message, ask: "Would you like me to polish/improve this message?"
     - If yes: Review and improve for clarity, conciseness, and Mozilla conventions. Remove verbosity, strengthen weak phrasing, ensure technical accuracy
     - If no: Use their message as-is

5. **Create commit or patch**:

   **If committing (recommended)**:
   - Stage files: `git add <files>`
   - Create commit:
     ```
     Bug <number> - <title>

     <detailed summary>

     Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
     ```
   - Show commit hash and explain: `git format-patch -1 HEAD` to export later

   **If creating patch**:
   - Filename: `bug-<number>-<slug>.patch`
   - Include commit-style message + git diff output
   - Save to current directory

## Commit Message Guidelines

- **Clarity and Conciseness**: Every word must earn its place. Remove filler, avoid redundancy
- **First line**: Concise title (50-72 chars) that clearly states what changed
- **Body**: Explain what and why, not how. Be direct and specific
- **Context**: Reference related commits or bugs only when it adds value
- **Details**: Include only essential technical specifics that reviewers need
- **Co-authored**: Always add Claude co-authorship line
- **Avoid**: Obvious statements, unnecessary adjectives, verbose explanations

## Example

```
Bug 2012791 - Fix CheckedInt overflow in AudioData::CopyTo

Adds isValid() check before calling value() on CheckedInt to prevent
assertion failures when integer overflow occurs during buffer size
calculation.

This complements the crashtest added in the previous commit, which
reproduces the fuzzer-found issue with large numberOfFrames values.

The fix ensures overflow is detected and a proper RangeError is thrown
instead of crashing.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Important

- Ask all questions in ONE call (not multiple rounds)
- Look at previous commits for context
- Commit is preferred over patch files
- **Commit messages must be CLEAR and CONCISE** - no verbosity, no fluff
- Whether generating or polishing, prioritize clarity and brevity over completeness
