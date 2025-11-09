---
description: Stage all changes and create a commit with a message
argument-hint: [commit message or empty to auto-generate]
allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*), Bash(git diff:*)
---

# Git Commit

Your task is to stage all changes and create a commit. If the user provides a message, use it. Otherwise, generate one based on the changes.

## Pre-Commit Context

First, review what will be committed:

**Git Status:**
!`git status`

**File Changes Summary:**
!`git diff --stat HEAD`

**Full Code Changes:**
!`git diff HEAD`

**Current Branch:**
!`git branch --show-current`

**Recent Commits (for style reference):**
!`git log --oneline -10`

## Your Task

1. **Analyze the changes** in the git diff above to understand:
   - What files changed
   - What functionality was added/modified/fixed
   - The scope of changes (auth, ui, db, etc.)

2. **Determine the commit message:**
   - If user provided `$ARGUMENTS`, use it as-is
   - If `$ARGUMENTS` is empty, generate a message using Conventional Commits format:
     - Format: `<type>(<scope>): <description>`
     - Types: feat, fix, refactor, docs, chore, test, perf
     - Base it on the actual code changes you see in the diff

3. **Execute the commit:**
```bash
git add .
git commit -m "<the commit message>"
```

4. **After committing, display:**
   - The commit hash and message
   - Number of files changed
   - Current branch status
   - Brief summary of what was committed

## Best Practices for High-Quality Commit Messages

A well-crafted commit message is the best way to communicate context about a change to other developers (and your future self).

### Format Guidelines

1. **Separate subject from body with a blank line.**

2. **Limit the subject line to 50 characters.**
   - Keeps them readable in commit logs

3. **Capitalize the subject line.**

4. **Do not end the subject line with a period.**

5. **Use the imperative mood in the subject line.**
   - A proper subject line should complete: "If applied, this commit will..."
   - ✅ Good: `Refactor user authentication module`
   - ❌ Bad: `Refactored user authentication module` or `Refactoring user auth`

6. **Wrap the body at 72 characters.**
   - Ensures readability in various git tools

7. **Use the body to explain what and why vs. how.**
   - The code itself shows how
   - The commit message should explain the reasoning behind the change

### Conventional Commits (Used in this project)

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

**Format:** `<type>(<scope>): <description>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements

**Examples:**
- `feat(auth): Add OAuth authentication flow`
- `fix(auth): Resolve token refresh race condition`
- `docs(readme): Update installation instructions`

### Project-Specific Conventions

This project includes:
- 🤖 Generated with [Claude Code](https://claude.com/claude-code)
- Co-Authored-By: Claude <noreply@anthropic.com>

For significant commits, consider using a detailed multiline format.
