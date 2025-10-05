# Google SSO with Supabase Implementation Plan

## Overview
Add Google Single Sign-On (SSO) authentication to the UMG web app using Supabase Auth. This will allow users to authenticate before submitting events, satisfying the Row Level Security (RLS) policies.

## Scope
- **What we're building**: Google OAuth login flow with Supabase Auth
- **What we're NOT building yet**: Multi-user support, user profiles, role-based access control

## Technical Requirements

### 1. Google Cloud Console Setup

#### Create OAuth 2.0 Credentials
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing project
3. Navigate to "APIs & Services" → "Credentials"
4. Click "Create Credentials" → "OAuth 2.0 Client ID"
5. Configure OAuth consent screen:
   - User Type: External (for testing)
   - App name: UMG - Unified Memory Graph
   - User support email: [your email]
   - Developer contact: [your email]
6. Create OAuth Client ID:
   - Application type: Web application
   - Name: UMG Web App
   - Authorized JavaScript origins:
     - `http://localhost:3110`
     - `https://mdcarckygvbcjgexvdqw.supabase.co`
   - Authorized redirect URIs:
     - `https://mdcarckygvbcjgexvdqw.supabase.co/auth/v1/callback`
7. Save the **Client ID** and **Client Secret**

### 2. Supabase Configuration

#### Enable Google Auth Provider
1. Go to Supabase Dashboard → Authentication → Providers
2. Enable Google provider
3. Enter the **Client ID** and **Client Secret** from Google Cloud Console
4. Save configuration

#### Update RLS Policies
The existing RLS policies already check for `auth.uid() IS NOT NULL`, so they should work once users are authenticated. No changes needed.

#### Optional: Add user_id column to raw_events
For future multi-user support, we may want to add a `user_id` column:
```sql
-- Optional: Add user_id column for future multi-user support
ALTER TABLE raw_events ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Update RLS policies to check ownership
DROP POLICY "Users can insert events" ON raw_events;
DROP POLICY "Users can read events" ON raw_events;

CREATE POLICY "Users can insert their own events"
  ON raw_events
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own events"
  ON raw_events
  FOR SELECT
  USING (auth.uid() = user_id);
```

**Decision**: For MVP, we'll skip the `user_id` column and just require authentication. The existing policies allow any authenticated user to insert/read events.

### 3. Shared Package Updates (`packages/db`)

#### Add Supabase Auth Helper Functions
- File: `packages/db/src/auth.ts`
- Export auth helper functions:
  - `signInWithGoogle()` - Initiates Google OAuth flow
  - `signOut()` - Signs out current user
  - `getCurrentUser()` - Gets current authenticated user
  - `onAuthStateChange()` - Listens for auth state changes

```typescript
import { supabase } from './index';

export const signInWithGoogle = async () => {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}/`,
    },
  });
  return { data, error };
};

export const signOut = async () => {
  const { error } = await supabase.auth.signOut();
  return { error };
};

export const getCurrentUser = async () => {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
};

export const onAuthStateChange = (callback: (user: any) => void) => {
  return supabase.auth.onAuthStateChange((event, session) => {
    callback(session?.user ?? null);
  });
};
```

#### Export from index.ts
```typescript
export * from './auth';
```

### 4. Web App Implementation (`apps/web`)

#### Create Auth Context/Provider (Optional but Recommended)
- File: `apps/web/contexts/AuthContext.tsx`
- Provides auth state throughout the app
- Handles loading states
- Manages session persistence

Alternative: Use auth state directly in components (simpler for MVP)

#### Update Layout to Handle Auth
- File: `apps/web/app/layout.tsx`
- Add auth session check
- Show sign-in prompt if not authenticated
- Optional: Add sign-out button in header

#### Create Sign-In Page/Component
- File: `apps/web/app/login/page.tsx` OR a modal/component in the home page
- Simple "Sign in with Google" button
- Handle OAuth redirect after successful sign-in

#### Update Home Page
- File: `apps/web/app/page.tsx`
- Check authentication state
- Show sign-in button if not authenticated
- Show capture form if authenticated
- Optional: Display user info (email, avatar)

#### Handle OAuth Callback
- Next.js App Router automatically handles the callback via Supabase
- No additional route needed (Supabase client handles token exchange)

### 5. Environment Variables

No new environment variables needed. The existing Supabase credentials will work for auth.

### 6. User Experience Flow

**First-time user**:
1. Visit http://localhost:3110
2. See "Sign in with Google" button
3. Click → redirected to Google OAuth consent screen
4. Approve → redirected back to app
5. Now authenticated, see the capture form

**Returning user**:
1. Visit http://localhost:3110
2. Supabase session persists in localStorage
3. Automatically authenticated
4. See the capture form immediately

**Sign out**:
1. Click "Sign Out" button (in header or settings)
2. Session cleared
3. Redirected to sign-in view

## Implementation Order

1. **Google Cloud Console Setup** ⏳
   - Create OAuth credentials
   - Configure consent screen
   - Get Client ID and Client Secret

2. **Supabase Configuration** ⏳
   - Enable Google auth provider
   - Enter OAuth credentials
   - Verify RLS policies are correct

3. **Shared Package Auth Helpers** (`packages/db`) ⏳
   - Create `src/auth.ts` with helper functions
   - Export from `src/index.ts`

4. **Web App Auth UI** (`apps/web`) ⏳
   - Update home page to check auth state
   - Add "Sign in with Google" button
   - Add sign-out functionality
   - Handle loading states

5. **Testing & Validation** ⏳
   - Sign in with Google
   - Submit an event (should work now)
   - Verify event saved in Supabase with proper auth context
   - Sign out and verify can't submit events
   - Sign in again and verify session persists

## Success Criteria

- [ ] User can click "Sign in with Google" button
- [ ] OAuth flow redirects to Google and back successfully
- [ ] User session persists across page refreshes
- [ ] Authenticated users can submit events without RLS errors
- [ ] Unauthenticated users see sign-in prompt, not the form
- [ ] User can sign out and session is cleared
- [ ] Events are saved with proper authentication context

## Design Considerations

### Minimal UI for MVP
- Simple centered "Sign in with Google" button when not authenticated
- Minimal header with user email + sign-out button when authenticated
- Keep the existing capture form UI

### Session Management
- Supabase handles session tokens automatically
- Sessions stored in localStorage
- Auto-refresh of tokens handled by Supabase client

### Error Handling
- Handle OAuth errors (user cancels, network issues)
- Handle auth state errors (expired tokens, etc.)
- Show friendly error messages

## Future Enhancements (Out of Scope for MVP)
- Email/password authentication
- Multi-factor authentication (MFA)
- User profile management
- User_id column in raw_events for multi-user support
- Role-based access control
- Social auth providers (GitHub, etc.)

---

**Estimated Time**: 1-2 hours
**Dependencies**: Google Cloud Console access, Supabase admin access
