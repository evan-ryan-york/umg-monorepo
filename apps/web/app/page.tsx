'use client';

import { useState, useEffect } from 'react';
import { supabase, signInWithGoogle, onAuthStateChange } from '@repo/db';
import type { User } from '@supabase/supabase-js';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { NavBar } from '@/components/NavBar';
import { CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

export default function Home(): React.ReactElement {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    // Listen for auth state changes
    const { data: { subscription } } = onAuthStateChange((user) => {
      setUser(user);
      setIsAuthLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const handleSignIn = async () => {
    const { error } = await signInWithGoogle();
    if (error) {
      setMessage({ type: 'error', text: 'Failed to sign in. Please try again.' });
    }
  };

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

      if (!session) {
        setMessage({ type: 'error', text: 'Not authenticated. Please sign in again.' });
        setIsLoading(false);
        return;
      }

      const response = await fetch('/api/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`,
        },
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

  if (isAuthLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted/20">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-3xl font-bold">UMG</CardTitle>
            <CardDescription className="text-base">
              Your Unified Memory Graph — capturing the meta-layer of your thinking
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Sign in to start capturing your thoughts, decisions, and insights
            </p>
            <Button onClick={handleSignIn} className="w-full gap-2" size="lg">
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Sign in with Google
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
          </CardContent>
        </Card>
      </div>
    );
  }

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
