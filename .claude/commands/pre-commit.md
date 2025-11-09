---
description: Run build and type checks before committing
allowed-tools: Bash(pnpm build:*), Bash(find:*)
---

# Pre-Commit Check

Your task is to analyze the results of the following pre-commit checks for this project.

## 1. Build Check

Run the project's build command to ensure there are no compilation errors.

**Build Output:**
!`pnpm build 2>&1 | tail -50`

## 2. TypeScript Syntax Check

This command verifies TypeScript syntax in Supabase Edge Functions.

**Edge Functions Found:**
!`find supabase/functions -name "*.ts" -type f`

**Note:** Edge Functions use Deno and are validated on deployment via `npx supabase functions deploy`.

## Analysis

Review the build output above.

**If there are errors:**
- Summarize them clearly
- Identify the problematic files and line numbers
- Provide specific suggestions on how to fix them

**If both checks pass successfully:**
Respond with: "✅ All pre-commit checks passed. Ready to commit."

Include:
- Number of build warnings (if any)
- Number of TypeScript files found
- Overall status
