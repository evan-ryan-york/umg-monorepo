import { NextResponse } from 'next/server';
import { createClient } from '@supabase/supabase-js';

interface EdgeData {
  id: string;
  from_id: string;
  to_id: string;
  kind: string;
  confidence?: number;
  importance?: number;
  description?: string;
  metadata?: Record<string, unknown>;
}

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '100', 10);
    const includeEdges = searchParams.get('includeEdges') !== 'false';

    // Create Supabase client with service role key
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // Fetch entities with signal data (importance scores)
    const { data: entities, error: entitiesError } = await supabase
      .from('entity')
      .select(`
        id,
        title,
        type,
        summary,
        metadata,
        created_at,
        signal (
          importance,
          recency,
          novelty
        )
      `)
      .order('created_at', { ascending: false })
      .limit(limit);

    if (entitiesError) {
      console.error('Error fetching entities:', entitiesError);
      return NextResponse.json(
        { error: 'Failed to fetch entities' },
        { status: 500 }
      );
    }

    let edges: EdgeData[] = [];
    if (includeEdges) {
      // Fetch edges (relationships between entities)
      const { data: edgesData, error: edgesError } = await supabase
        .from('edge')
        .select('id, from_id, to_id, kind, confidence, importance, description, metadata');

      if (edgesError) {
        console.error('Error fetching edges:', edgesError);
      } else {
        edges = edgesData || [];
        console.log(`Fetched ${edges.length} edges`);
      }
    }

    return NextResponse.json({
      entities: entities || [],
      edges: edges,
      total: entities?.length || 0
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
