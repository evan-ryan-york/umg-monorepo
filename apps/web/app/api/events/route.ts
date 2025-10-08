import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
import type { SupabaseClient } from '@supabase/supabase-js';
import type { RawEventInsert } from '@repo/db';

export async function POST(request: Request) {
  try {
    // Get the authorization header from the request
    const authHeader = request.headers.get('authorization');

    if (!authHeader) {
      return NextResponse.json(
        { success: false, error: 'Unauthorized' },
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
    const { content, source } = body;

    // Validate input
    if (!content || typeof content !== 'string' || content.trim().length === 0) {
      return NextResponse.json(
        { success: false, error: 'Content is required and must be a non-empty string' },
        { status: 400 }
      );
    }

    // Get or create user entity
    // Note: This might be null on first event - Archivist will create it during processing
    const userEntityId = await getUserEntityId(supabase);

    // Prepare the event data
    const eventData: RawEventInsert = {
      payload: {
        type: 'text',
        content: content.trim(),
        metadata: {},
        user_id: 'default_user', // Will be from auth when implemented
        user_entity_id: userEntityId || undefined, // Allow null for first event
      },
      source: source || 'quick_capture',
      status: 'pending_processing', // Manual entries skip triage
    };

    // Insert into Supabase
    const { data, error } = await supabase
      .from('raw_events')
      .insert(eventData)
      .select('id')
      .single();

    if (error) {
      console.error('Supabase error:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to save event to database' },
        { status: 500 }
      );
    }

    // Return success response
    return NextResponse.json({
      success: true,
      id: data.id,
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}

/**
 * Get or create the user entity for the current user
 * Returns the entity ID, or null if unable to find/create
 */
async function getUserEntityId(supabase: SupabaseClient): Promise<string | null> {
  console.log('\n🔍 [DEBUG] getUserEntityId() called');

  try {
    // Look for Ryan York's person entity
    console.log('🔍 [DEBUG] Querying for person entities with "Ryan York" in title...');
    const { data: existingEntities, error: queryError } = await supabase
      .from('entity')
      .select('id, title, type, metadata')
      .eq('type', 'person')
      .ilike('title', '%Ryan York%'); // Find entity with "Ryan York" in title

    if (queryError) {
      console.error('❌ [DEBUG] Error querying for Ryan York entity:', queryError);
      return null;
    }

    console.log(`🔍 [DEBUG] Query returned ${existingEntities?.length || 0} entities`);
    if (existingEntities && existingEntities.length > 0) {
      existingEntities.forEach((entity, index) => {
        console.log(`🔍 [DEBUG] Entity ${index + 1}:`, {
          id: entity.id,
          title: entity.title,
          type: entity.type,
          metadata: entity.metadata,
        });
      });

      const firstEntity = existingEntities[0];
      if (firstEntity) {
        console.log(`✅ [DEBUG] Found Ryan York entity: ${firstEntity.id} (${firstEntity.title})`);
        console.log(`✅ [DEBUG] Metadata:`, firstEntity.metadata);
        return firstEntity.id;
      }
    }

    // Ryan York entity doesn't exist yet
    // DON'T create it here - let the Archivist create it on first introduction
    console.log(`⚠️  [DEBUG] No Ryan York entity found - will be created by Archivist on self-introduction`);
    return null;
  } catch (error) {
    console.error('❌ [DEBUG] Exception in getUserEntityId:', error);
    return null;
  }
}
