---
description: Switch to main, pull latest changes, and delete the previous branch
allowed-tools: Bash(git checkout:*), Bash(git switch:*), Bash(git pull:*), Bash(git branch:*)
---

# Pull Main and Delete Previous Branch

This command helps you clean up after a PR is merged by switching to main, pulling the latest changes, and deleting your feature branch.

## Pre-Execution Context

Before switching branches, let's understand the current state:

**Current Branch:**
!`git branch --show-current`

**Branch Status:**
!`git status --short`

**Local Branches:**
!`git branch -vv`

## Your Task

1. **Check for uncommitted changes**
   - If there are uncommitted changes, warn the user and ask if they want to:
     - Stash changes and proceed
     - Commit changes first
     - Abort the operation

2. **Store the current branch name**
   - Save the current branch name to delete it later
   - If already on main, inform the user and just pull

3. **Switch to main branch**
   ```bash
   git checkout main
   ```
   Or use:
   ```bash
   git switch main
   ```

4. **Pull latest changes from remote**
   ```bash
   git pull origin main
   ```

5. **Delete the previous branch (soft delete)**
   ```bash
   git branch -d <previous-branch-name>
   ```

   **Note:** Use `-d` (lowercase) for soft delete, which prevents deletion if:
   - The branch hasn't been merged
   - The branch has unpushed commits

   If the delete fails, inform the user they can force delete with:
   ```bash
   git branch -D <branch-name>
   ```

6. **Display summary**
   Show:
   - Current branch (should be main)
   - Latest commits on main
   - Confirmation that the branch was deleted
   - List of remaining local branches

## Safety Checks

### Before Switching Branches

If there are uncommitted changes, ask the user:

```
⚠️  You have uncommitted changes on <branch-name>:
<list of modified files>

What would you like to do?
1. Stash changes and proceed (recommended)
2. Abort operation (you can commit first)
```

If user chooses stash, run:
```bash
git stash push -m "Auto-stash before switching to main"
```

### Before Deleting Branch

- Don't delete if currently on that branch (should be impossible after switching)
- Don't delete the main branch
- Use soft delete `-d` to prevent accidental loss of unmerged work

## Example Execution

```bash
# 1. Store current branch
PREV_BRANCH=$(git branch --show-current)

# 2. Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
  echo "⚠️  Uncommitted changes detected"
  # (handle user choice to stash or abort)
fi

# 3. Switch to main
git checkout main

# 4. Pull latest changes
git pull origin main

# 5. Delete previous branch
git branch -d "$PREV_BRANCH"

# 6. Show summary
echo "✅ Switched to main and deleted $PREV_BRANCH"
git log --oneline -5
git branch -vv
```

## Expected Output

After successful execution, display:

```
✅ Branch Cleanup Complete

Previous branch: feature/my-feature
Current branch: main
Deleted: feature/my-feature

Latest commits on main:
<git log --oneline -5>

Remaining local branches:
<git branch -vv>
```

## Error Handling

### Branch Not Fully Merged

If `git branch -d` fails with "not fully merged":

```
❌ Branch '<branch-name>' is not fully merged.

This usually means:
- The PR wasn't merged yet
- There are local commits not pushed
- The branch wasn't merged into main

To force delete anyway:
git branch -D <branch-name>

Or check if the PR is merged on GitHub:
gh pr view <pr-number>
```

### Already on Main

If the user is already on main:

```
ℹ️  Already on main branch.
Pulling latest changes...

✅ Main branch updated
<show latest commits>
```

## Best Practices

1. **Always use this command after a PR is merged**
   - Keeps your local repository clean
   - Ensures you have the latest changes from main

2. **Check PR status first**
   ```bash
   gh pr view <pr-number>
   ```
   Make sure the PR is merged before deleting the branch

3. **Soft delete is safer**
   - `-d` prevents accidental deletion of unmerged work
   - Only use `-D` if you're absolutely sure

4. **Regular cleanup**
   - Run this after every merged PR
   - Keeps your `git branch` list manageable

## See Also

- `/pr-submit` - Submit a pull request
- `/commit` - Create a commit with auto-generated message
- `git branch -a` - View all local and remote branches
