'use client';

import { useState, useEffect } from 'react';
import { supabase, onAuthStateChange } from '@repo/db';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export default function Home(): React.ReactElement {
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    // Listen for auth state changes (development mode - not enforcing auth)
    const { data: { subscription } } = onAuthStateChange(() => {
      // Auth state tracking for future use
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!content.trim()) {
      setMessage({ type: 'error', text: 'Please enter some content' });
      return;
    }

    setIsLoading(true);
    setMessage(null);

    try {
      // Get the current session token
      const { data: { session } } = await supabase.auth.getSession();

      // DEVELOPMENT MODE: Allow submission without auth
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`;
      }

      const response = await fetch('/api/events', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          content: content.trim(),
          source: 'quick_capture',
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: 'Captured successfully! The Archivist will process this within 60 seconds.' });
        setContent('');
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to save event' });
      }
    } catch (error) {
      console.error('Submit error:', error);
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setIsLoading(false);
    }
  };

  // DEVELOPMENT MODE: Skip auth requirement (remove this in production!)
  // Keeping this commented out for now - uncomment to require auth:
  // if (isAuthLoading) {
  //   return (
  //     <div className="min-h-screen flex items-center justify-center">
  //       <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
  //     </div>
  //   );
  // }
  //
  // if (!user) {
  //   return (
  //     <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/20">
  //       ... sign-in UI ...
  //     </div>
  //   );
  // }

  return (
    <div className="min-h-screen bg-background">
      <main className="container mx-auto px-4 py-12 max-w-3xl">
        <div className="space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Quick Capture</h1>
            <p className="text-muted-foreground text-lg">
              Capture your thoughts, decisions, and insights. The Archivist will transform them into structured knowledge.
            </p>
          </div>

          <Card>
            <CardContent className="pt-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="What's on your mind? Share a thought, decision, reflection, or anything worth remembering..."
                    className="min-h-[200px] resize-y text-base"
                    disabled={isLoading}
                  />
                  <p className="text-xs text-muted-foreground">
                    The Archivist will extract entities, relationships, and signals from your input.
                  </p>
                </div>

                <Button
                  type="submit"
                  className="w-full"
                  size="lg"
                  disabled={isLoading || !content.trim()}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Capturing...
                    </>
                  ) : (
                    'Capture Thought'
                  )}
                </Button>

                {message && (
                  <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
                    {message.type === 'error' ? (
                      <AlertCircle className="h-4 w-4" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    <AlertDescription>{message.text}</AlertDescription>
                  </Alert>
                )}
              </form>
            </CardContent>
          </Card>

          <Card className="bg-muted/50">
            <CardHeader>
              <CardTitle className="text-sm font-medium">How it works</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm text-muted-foreground">
              <div className="flex gap-3">
                <span className="font-bold">1.</span>
                <span>You capture your thought here (zero friction)</span>
              </div>
              <div className="flex gap-3">
                <span className="font-bold">2.</span>
                <span>The Archivist extracts people, projects, decisions, and relationships</span>
              </div>
              <div className="flex gap-3">
                <span className="font-bold">3.</span>
                <span>Your knowledge graph grows, making past insights searchable and connected</span>
              </div>
              <div className="flex gap-3">
                <span className="font-bold">4.</span>
                <span>The Mentor surfaces insights to keep you aligned with your goals</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  );
}
