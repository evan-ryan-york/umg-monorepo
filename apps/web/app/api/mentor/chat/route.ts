import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';

const AI_CORE_URL = process.env.AI_CORE_URL || 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    // Get the authorization header from the request
    const authHeader = request.headers.get('authorization');

    if (!authHeader) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // Create a Supabase client with the user's auth token
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      {
        global: {
          headers: {
            Authorization: authHeader,
          },
        },
      }
    );

    // Parse request body
    const body = await request.json();
    const { message, conversation_history } = body;

    // Validate input
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return NextResponse.json(
        { error: 'Message is required and must be a non-empty string' },
        { status: 400 }
      );
    }

    // Get user entity ID
    const userEntityId = await getUserEntityId(supabase);

    // Call AI Core chat endpoint
    const aiCoreResponse = await fetch(`${AI_CORE_URL}/mentor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message.trim(),
        conversation_history: conversation_history || [],
        user_entity_id: userEntityId,
      }),
    });

    if (!aiCoreResponse.ok) {
      const errorText = await aiCoreResponse.text();
      console.error('AI Core error:', errorText);
      return NextResponse.json(
        { error: `AI Core error: ${aiCoreResponse.statusText}` },
        { status: aiCoreResponse.status }
      );
    }

    const data = await aiCoreResponse.json();

    return NextResponse.json(data);
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Failed to process chat message' },
      { status: 500 }
    );
  }
}

/**
 * Get the user entity ID for the current user
 * Returns the entity ID, or null if unable to find
 */
async function getUserEntityId(supabase: SupabaseClient): Promise<string | null> {
  try {
    const { data: existingEntities, error: queryError } = await supabase
      .from('entity')
      .select('id, title, metadata')
      .eq('type', 'person')
      .ilike('title', '%Ryan York%');

    if (queryError) {
      console.error('Error querying for Ryan York entity:', queryError);
      return null;
    }

    if (existingEntities && existingEntities.length > 0) {
      // Prefer entity with is_user_entity: true
      const userEntity = existingEntities.find(
        (e) => e.metadata?.is_user_entity === true
      );
      if (userEntity) return userEntity.id;
      if (existingEntities[0]) return existingEntities[0].id;
    }

    return null;
  } catch (error) {
    console.error('Exception in getUserEntityId:', error);
    return null;
  }
}
