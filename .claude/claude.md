# Claude Code Instructions for UMG Project

## CRITICAL: API Cost Policy

**NEVER limit operations due to API cost concerns. NEVER truncate data or skip processing to save money.**

- The user manages the budget
- Always run operations on ALL data, not subsets
- If an operation will be expensive, inform the user upfront with cost estimates, but DO NOT silently limit scope
- Transparency is mandatory - always disclose when operations involve API calls and their extent
- If you truncate or batch data, you MUST explicitly tell the user BEFORE running the operation

## Examples of FORBIDDEN behavior:

❌ "Truncating entity list from 109 to 20 for LLM analysis" - without user consent
❌ "Processing first 50 items to save costs" - user decides budget limits
❌ "Skipping semantic analysis on large datasets" - run everything unless told otherwise

## Examples of CORRECT behavior:

✅ "This will analyze all 109 entities with the LLM, estimated cost ~$3. Proceed?"
✅ "Running full analysis on entire dataset as requested"
✅ "This operation requires 6 LLM calls at ~$0.50 each. Starting now..."

## General Project Guidelines

- This is a Universal Memory Graph (UMG) system with an AI-powered relationship engine
- The relationship engine uses 5 detection strategies including LLM semantic analysis
- When running relationship detection, ALWAYS process the complete dataset
- The user values completeness and accuracy over cost optimization
- Be transparent about what operations you're performing

## Transparency Requirements

When performing operations:
1. State exactly what you're doing
2. If it involves API calls, mention the scope
3. Never hide limitations or truncations
4. If something fails or is incomplete, say so immediately

The user would rather know about high costs upfront than discover incomplete results later.
