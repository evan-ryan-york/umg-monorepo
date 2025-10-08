import { createClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';

export async function POST(): Promise<NextResponse> {
  try {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // Delete in order to respect foreign key constraints
    // 1. Delete embeddings (references chunks)
    const { error: embeddingsError } = await supabase
      .from('embedding')
      .delete()
      .neq('chunk_id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (embeddingsError) {
      console.error('Error deleting embeddings:', embeddingsError);
      throw embeddingsError;
    }

    // 2. Delete chunks (references entities)
    const { error: chunksError } = await supabase
      .from('chunk')
      .delete()
      .neq('entity_id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (chunksError) {
      console.error('Error deleting chunks:', chunksError);
      throw chunksError;
    }

    // 3. Delete signals (references entities)
    const { error: signalsError } = await supabase
      .from('signal')
      .delete()
      .neq('entity_id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (signalsError) {
      console.error('Error deleting signals:', signalsError);
      throw signalsError;
    }

    // 4. Delete edges (references entities)
    const { error: edgesError } = await supabase
      .from('edge')
      .delete()
      .neq('from_id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (edgesError) {
      console.error('Error deleting edges:', edgesError);
      throw edgesError;
    }

    // 5. Delete entities
    const { error: entitiesError } = await supabase
      .from('entity')
      .delete()
      .neq('id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (entitiesError) {
      console.error('Error deleting entities:', entitiesError);
      throw entitiesError;
    }

    // 6. Delete raw_events
    const { error: eventsError } = await supabase
      .from('raw_events')
      .delete()
      .neq('id', '00000000-0000-0000-0000-000000000000'); // Delete all

    if (eventsError) {
      console.error('Error deleting raw_events:', eventsError);
      throw eventsError;
    }

    return NextResponse.json({
      success: true,
      message: 'All Archivist data cleared successfully',
    });
  } catch (error) {
    console.error('Error resetting Archivist data:', error);
    return NextResponse.json(
      {
        success: false,
        error: 'Failed to reset Archivist data',
      },
      { status: 500 }
    );
  }
}
