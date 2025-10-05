# Raw Text Input Implementation Plan

## Overview
Build a basic text input system for the web app that allows users to submit raw text data, which will be saved to the `raw_events` table in Supabase.

## Scope
- **What we're building**: A simple text field with a submit button on the home page of `apps/web`
- **What we're NOT building yet**: Guided opening/closing prompts, voice input, or any other capture methods

## Technical Requirements

### 1. Database Setup (Supabase)

#### Create the `raw_events` table
```sql
CREATE TABLE raw_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  payload JSONB NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending_triage',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Add index for status queries
CREATE INDEX idx_raw_events_status ON raw_events(status);
CREATE INDEX idx_raw_events_created_at ON raw_events(created_at DESC);
```

#### Enable Row Level Security (RLS)
```sql
ALTER TABLE raw_events ENABLE ROW LEVEL SECURITY;

-- Policy: Allow authenticated users to insert their own events
CREATE POLICY "Users can insert their own events"
  ON raw_events
  FOR INSERT
  WITH CHECK (auth.uid() IS NOT NULL);

-- Policy: Allow authenticated users to read their own events
CREATE POLICY "Users can read their own events"
  ON raw_events
  FOR SELECT
  USING (auth.uid() IS NOT NULL);
```

**Note**: We may need to add a `user_id` column to `raw_events` for proper multi-user support. For MVP, we can assume single-user and skip this.

### 2. Shared Package Setup (`packages/db`)

#### Update/Create Supabase Client and Types
- File: `packages/db/src/index.ts`
- Initialize Supabase client with project URL and anon key
- Define `RawEvent` interface matching the database schema
- Define `RawEventInsert` type for new event creation
- Define `RawEventPayload` type for the JSONB payload structure
- Export client and all types for use across apps

```typescript
export interface RawEvent {
  id: string;
  payload: RawEventPayload;
  source: string;
  status: string;
  created_at: string;
}

export interface RawEventInsert {
  payload: RawEventPayload;
  source: string;
  status?: string;
}

export interface RawEventPayload {
  type: 'text' | 'voice' | 'webhook';
  content: string;
  metadata?: Record<string, any>;
}
```

### 3. Web App Implementation (`apps/web`)

#### Add `@repo/db` Dependency
- File: `apps/web/package.json`
- Add `"@repo/db": "*"` to dependencies
- Run `pnpm install` to link the workspace package

#### API Route: `/api/events`
- File: `apps/web/app/api/events/route.ts` (App Router) or `apps/web/pages/api/events.ts` (Pages Router)
- Accept POST requests with JSON body containing `content` and `source`
- Validate input (non-empty content, valid source)
- Insert into `raw_events` table via Supabase client
- Return success/error response

**Request Body Schema**:
```json
{
  "content": "string (required)",
  "source": "string (optional, defaults to 'quick_capture')"
}
```

**Response Schema**:
```json
{
  "success": true,
  "id": "uuid-of-created-event"
}
```

#### Home Page Component
- File: `apps/web/app/page.tsx` (App Router) or `apps/web/pages/index.tsx` (Pages Router)
- Create a simple form with:
  - Textarea for text input (multi-line support)
  - Submit button
  - Loading state during submission
  - Success/error message display
  - Clear input after successful submission

**UI Requirements**:
- Textarea should be reasonably sized (e.g., 4-5 rows minimum)
- Submit button should be disabled during submission
- Show clear feedback on success/error
- Simple, clean design (can be basic for MVP)

### 4. Environment Variables

#### Required in `apps/web/.env.local`
```
NEXT_PUBLIC_SUPABASE_URL=your-project-url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

### 5. Dependencies to Install

#### In `packages/db`
```bash
# Already installed in packages/db/package.json
@supabase/supabase-js: ^2.49.2
```

#### In `apps/web`
```bash
# Add to package.json dependencies
"@repo/db": "*"

# Install Tailwind CSS PostCSS plugin
pnpm add -D @tailwindcss/postcss
```

#### Update PostCSS Configuration
- File: `apps/web/postcss.config.mjs`
- Change `tailwindcss: {}` to `'@tailwindcss/postcss': {}`
- This fixes compatibility with Tailwind CSS v4

## Implementation Order

1. **Database Setup** (Supabase Dashboard) ✅ COMPLETED
   - Create `raw_events` table (and all other tables in schema)
   - Set up RLS policies
   - Add indexes for performance
   - Test manual insert via SQL editor

2. **Shared Package** (`packages/db`) ✅ COMPLETED
   - Set up Supabase client in `src/index.ts`
   - Define TypeScript types (RawEvent, RawEventInsert, RawEventPayload)
   - Define types for all other tables (Entity, Edge, Chunk, etc.)
   - Export client and types

3. **Environment Setup** (`apps/web`) ✅ COMPLETED
   - Create `.env.local` with Supabase credentials
   - Add `@repo/db` dependency to `package.json`
   - Install `@tailwindcss/postcss`
   - Update `postcss.config.mjs`
   - Run `pnpm install`

4. **API Route** (`apps/web`) ✅ COMPLETED
   - Create `/api/events/route.ts` endpoint
   - Implement validation and database insert logic
   - Add error handling
   - Test with browser network tab

5. **Frontend Component** (`apps/web`) ✅ COMPLETED
   - Replace default home page with text input form
   - Add textarea with placeholder
   - Add submit button with disabled state
   - Wire up form submission to API route
   - Add loading state during submission
   - Add success/error message display
   - Clear input after successful submission
   - Style with CSS modules

6. **Testing & Validation** ✅ COMPLETED
   - Start dev server (`pnpm --filter web dev --port 3001`)
   - Open http://localhost:3001
   - Submit test data via UI
   - Verify success message appears
   - Verify data appears correctly in Supabase dashboard
   - Check all required fields are populated
   - Verify payload structure is correct

## Success Criteria

- [x] User can type text into a textarea on the home page
- [x] User can click submit button to save the text
- [x] Submitted text appears in `raw_events` table with:
  - Correct `payload` structure containing the text
  - `source` set to 'quick_capture'
  - `status` set to 'pending_triage'
  - `created_at` timestamp
- [x] UI shows loading state during submission
- [x] UI shows success message after submission
- [x] UI shows error message if submission fails
- [x] Input field clears after successful submission

## Implementation Complete! ✅

**All phases completed successfully on 2025-10-03**

The raw text input feature is now fully functional. Users can submit text through the web interface at http://localhost:3001, and the data is properly saved to the Supabase `raw_events` table with the correct structure.

## Future Enhancements (Out of Scope for MVP)
- Guided opening questions
- Guided closing questions
- Voice input integration
- Keyboard shortcuts for quick capture
- Rich text editing
- Draft saving
- Offline support
