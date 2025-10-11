import { InsightCard } from '@/components/InsightCard';
import { createClient } from '@supabase/supabase-js';

export const dynamic = 'force-dynamic';

interface Insight {
  id: string;
  title: string;
  body: string;
  drivers: {
    entity_ids: string[];
    edge_ids: string[];
  };
  status: string;
  created_at: string;
}

export default async function DigestPage(): Promise<React.JSX.Element> {
  let insights: Insight[] = [];
  let error: string | null = null;

  try {
    // Create Supabase client with service role key for server-side access
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.SUPABASE_SERVICE_ROLE_KEY!
    );

    // Fetch open insights
    const { data, error: fetchError } = await supabase
      .from('insight')
      .select('*')
      .eq('status', 'open')
      .order('created_at', { ascending: false })
      .limit(10);

    if (fetchError) {
      console.error('Error fetching insights:', fetchError);
      error = 'Failed to fetch insights';
    } else {
      insights = data || [];
    }
  } catch (e) {
    console.error('Error in digest page:', e);
    error = 'Error loading digest';
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">🌅 Daily Digest</h1>
        <p className="text-gray-600">
          {new Date().toLocaleDateString('en-US', {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric',
          })}
        </p>
      </div>

      {/* Explanation Panel */}
      <div className="mb-6 bg-purple-50 border border-purple-200 rounded-lg p-4">
        <h2 className="font-semibold text-purple-900 mb-2">💡 About Your Daily Digest</h2>
        <div className="text-sm text-purple-800 space-y-2">
          <p>
            <strong>Delta Watch (📊):</strong> Compares your stated goals with actual work.
            Celebrates alignment or highlights drift to help you stay intentional.
          </p>
          <p>
            <strong>Connection (🔗):</strong> Surfaces relevant context from your past work.
            Helps you learn from experience and avoid repeating mistakes.
          </p>
          <p>
            <strong>Prompt (❓):</strong> Asks a challenging, forward-looking question.
            Designed to deepen your thinking and expose blindspots.
          </p>
          <p className="text-xs mt-3 pt-2 border-t border-purple-300">
            <strong>How to respond:</strong> Click <span className="font-semibold">👍 Acknowledge</span> if
            an insight is valuable (boosts related topics), or{' '}
            <span className="font-semibold">👎 Dismiss</span> if it&apos;s not helpful (avoids similar
            insights in future).
          </p>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="text-red-600 bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
          {error}
        </div>
      )}

      {/* Empty State */}
      {!error && insights.length === 0 && (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600 text-lg mb-2">No insights generated yet</p>
          <p className="text-gray-500 text-sm">
            The Mentor will create your daily digest soon. Make sure you have some entities in your
            knowledge graph by using Quick Capture.
          </p>
        </div>
      )}

      {/* Insights */}
      {!error && insights.length > 0 && (
        <div className="space-y-6">
          {insights.map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      )}

      {/* Footer Help */}
      {!error && insights.length > 0 && (
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            Your feedback trains the system. Insights adapt based on what you find valuable.
          </p>
        </div>
      )}
    </div>
  );
}
