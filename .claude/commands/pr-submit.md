---
description: Push branch to remote and create a GitHub pull request
argument-hint: [PR title or empty to auto-generate]
allowed-tools: Bash(git push:*), Bash(git status:*), Bash(git log:*), Bash(git diff:*), Bash(gh pr create:*)
---

# Submit Pull Request

This command will push your current branch to the remote repository and create a new pull request using the GitHub CLI.

**Note:** Requires the GitHub CLI (`gh`) to be installed and authenticated.

## Pre-PR Context

Review your changes before creating the PR:

**Current Branch:**
!`git branch --show-current`

**Branch Status:**
!`git status`

**Commits on this Branch:**
!`git log origin/main..HEAD --oneline`

**Full Commit Messages:**
!`git log origin/main..HEAD --format="%h - %s%n%b"`

**File Changes Summary:**
!`git diff --stat origin/main...HEAD`

**Full Code Changes:**
!`git diff origin/main...HEAD`

## Your Task

1. **Analyze all the context above** to understand:
   - What commits are being merged
   - What code changes were made
   - The overall feature/fix being introduced
   - What files and areas were affected

2. **Generate PR content:**
   - **If user provided `$ARGUMENTS`:** Use it as the PR title
   - **If `$ARGUMENTS` is empty:** Generate a title from the commits and changes
     - Use Conventional Commits format: `<type>(<scope>): <description>`
     - Make it descriptive and match the main purpose of the PR

   - **PR Body:** Always generate based on actual changes:
     - Summary: 2-3 bullet points of what this PR does
     - Changes Made: List key modifications from the diff
     - Testing: Include appropriate checklist items
     - Reference commit messages for details

3. **Execute:**
```bash
# Push current branch to remote
git push -u origin HEAD

# Create pull request
gh pr create --title "<your generated or user-provided title>" --body "<your generated body>"
```

4. **After PR is created, display:**
   - The PR URL
   - Number of commits included
   - Files changed summary
   - Brief description of what was merged

## Best Practices for High-Quality Pull Requests

A clear PR description helps reviewers understand your changes, reduces back-and-forth, and speeds up the merge process.

### 1. Write a Clear and Descriptive Title

The title is the first thing a reviewer sees. It should concisely summarize the purpose of the change.

- ✅ Good: `feat(auth): Implement OAuth authentication flow`
- ❌ Bad: `Made some changes`

**This project uses Conventional Commits format:**
- `feat(scope): Description` - New features
- `fix(scope): Description` - Bug fixes
- `chore(scope): Description` - Maintenance
- `docs(scope): Description` - Documentation

### 2. Provide Context in the Description

Explain the "why" behind your changes:

- **What problem does this PR solve?**
- **Is there a link to a ticket?** Include it!
- **What was the state before this change?**

### 3. Detail the Changes Made

Briefly describe your approach and key changes:

- "Added AuthService for OAuth authentication"
- "Refactored UserViewModel to handle auth state"
- "Updated Edge Function to validate access tokens"

### 4. Include Testing Instructions

Provide clear, step-by-step testing instructions:

**Example:**
1. Build and run the app
2. Navigate to the feature being tested
3. Perform the specific actions required
4. Verify expected behavior occurs
5. Check that data persists correctly

### 5. Use Visuals for UI Changes

If your PR involves UI changes, include:
- Screenshots
- GIFs or screen recordings
- Before/After comparisons

### 6. Keep Pull Requests Small and Focused

A PR should ideally do one thing well:

- ✅ Single feature or bug fix
- ✅ Under 500 lines of changes (ideal)
- ✅ Related changes grouped together
- ❌ Multiple unrelated features

### 7. Reference Related Issues

Link to related issues or tickets:

```markdown
Closes #123
Relates to #456
```

### Project-Specific Checklist

Ensure your PR includes:

- [ ] **Build**: Project builds successfully with no errors
- [ ] **Tests**: All tests pass
- [ ] **Edge Functions**: Deployed to Supabase if changed
- [ ] **Database**: Migrations applied if schema changed
- [ ] **Documentation**: Updated if API or features changed

### Common PR Scopes

Use these scopes in your PR titles to indicate the area of change:

- `feat` - New features
- `fix` - Bug fixes
- `auth` - Authentication and user management
- `ui` - User interface components
- `db` - Database schema or queries
- `edge-functions` - Supabase Edge Functions
- `docs` - Documentation updates
- `chore` - Maintenance tasks
