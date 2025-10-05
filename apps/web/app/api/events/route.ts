import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';
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

    // Prepare the event data
    const eventData: RawEventInsert = {
      payload: {
        type: 'text',
        content: content.trim(),
        metadata: {},
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
