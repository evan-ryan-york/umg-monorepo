import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

/**
 * GET /api/insights
 * Fetch insights from the database
 *
 * Query params:
 *   - status: Filter by status (open, acknowledged, dismissed)
 *   - limit: Max number of insights to return (default: 10)
 */
export async function GET(request: Request) {
  try {
    // Create Supabase client with service role key for admin access
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // Parse query parameters
    const { searchParams } = new URL(request.url);
    const status = searchParams.get('status') || 'open';
    const limit = parseInt(searchParams.get('limit') || '10', 10);

    // Query insights
    let query = supabase
      .from('insight')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(limit);

    // Filter by status if provided
    if (status) {
      query = query.eq('status', status);
    }

    const { data: insights, error } = await query;

    if (error) {
      console.error('Error fetching insights:', error);
      return NextResponse.json(
        { success: false, error: 'Failed to fetch insights' },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      insights: insights || [],
      count: insights?.length || 0,
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { success: false, error: 'Internal server error' },
      { status: 500 }
    );
  }
}
