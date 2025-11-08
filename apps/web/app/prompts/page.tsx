'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { CheckCircle2, AlertCircle, Save, RefreshCw } from 'lucide-react';

interface Prompt {
  name: string;
  filename: string;
}

export default function PromptsPage(): React.JSX.Element {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [content, setContent] = useState<string>('');
  const [originalContent, setOriginalContent] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load list of prompts
  useEffect(() => {
    loadPrompts();
  }, []);

  const loadPrompts = async () => {
    try {
      const response = await fetch('/api/prompts');
      const data = await response.json();
      setPrompts(data.prompts || []);

      // Auto-select first prompt
      if (data.prompts && data.prompts.length > 0 && !selectedPrompt) {
        setSelectedPrompt(data.prompts[0].name);
      }
    } catch (error) {
      console.error('Failed to load prompts:', error);
      setMessage({ type: 'error', text: 'Failed to load prompts' });
    }
  };

  // Load selected prompt content
  useEffect(() => {
    if (selectedPrompt) {
      loadPromptContent(selectedPrompt);
    }
  }, [selectedPrompt]);

  const loadPromptContent = async (name: string) => {
    setIsLoading(true);
    setMessage(null);

    try {
      const response = await fetch(`/api/prompts?name=${name}`);
      const data = await response.json();

      if (data.content) {
        setContent(data.content);
        setOriginalContent(data.content);
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to load prompt' });
      }
    } catch (error) {
      console.error('Failed to load prompt content:', error);
      setMessage({ type: 'error', text: 'Failed to load prompt content' });
    } finally {
      setIsLoading(false);
    }
  };

  const savePrompt = async () => {
    if (!selectedPrompt) return;

    setIsSaving(true);
    setMessage(null);

    try {
      const response = await fetch('/api/prompts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: selectedPrompt,
          content,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setMessage({ type: 'success', text: 'Prompt saved successfully! Changes will be live immediately.' });
        setOriginalContent(content);
      } else {
        setMessage({ type: 'error', text: data.error || 'Failed to save prompt' });
      }
    } catch (error) {
      console.error('Failed to save prompt:', error);
      setMessage({ type: 'error', text: 'Failed to save prompt' });
    } finally {
      setIsSaving(false);
    }
  };

  const resetContent = () => {
    setContent(originalContent);
    setMessage(null);
  };

  const hasChanges = content !== originalContent;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <h1 className="text-2xl font-bold text-gray-900">Prompt Editor</h1>
          <p className="text-sm text-gray-600 mt-1">
            Edit prompts for AI agents. Changes take effect immediately (hot-reload).
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-12 gap-6">
          {/* Sidebar */}
          <div className="col-span-3">
            <div className="bg-white rounded-lg border border-gray-200 p-4">
              <h2 className="text-sm font-semibold text-gray-900 mb-3">Available Prompts</h2>
              <div className="space-y-1">
                {prompts.map((prompt) => (
                  <button
                    key={prompt.name}
                    onClick={() => setSelectedPrompt(prompt.name)}
                    className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                      selectedPrompt === prompt.name
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {prompt.name}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Editor */}
          <div className="col-span-9">
            <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
              {/* Toolbar */}
              <div className="bg-gray-50 border-b border-gray-200 px-4 py-3 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-700">
                    {selectedPrompt || 'No prompt selected'}
                  </span>
                  {hasChanges && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                      Unsaved changes
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={resetContent}
                    variant="outline"
                    size="sm"
                    disabled={!hasChanges || isSaving}
                  >
                    <RefreshCw className="h-4 w-4 mr-1" />
                    Reset
                  </Button>
                  <Button
                    onClick={savePrompt}
                    size="sm"
                    disabled={!hasChanges || isSaving}
                  >
                    <Save className="h-4 w-4 mr-1" />
                    {isSaving ? 'Saving...' : 'Save'}
                  </Button>
                </div>
              </div>

              {/* Message */}
              {message && (
                <div className="px-4 py-3 border-b border-gray-200">
                  <Alert variant={message.type === 'error' ? 'destructive' : 'default'}>
                    {message.type === 'error' ? (
                      <AlertCircle className="h-4 w-4" />
                    ) : (
                      <CheckCircle2 className="h-4 w-4" />
                    )}
                    <AlertDescription>{message.text}</AlertDescription>
                  </Alert>
                </div>
              )}

              {/* Editor */}
              {isLoading ? (
                <div className="p-8 text-center text-gray-500">
                  Loading prompt...
                </div>
              ) : (
                <div className="relative">
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    className="w-full h-[calc(100vh-300px)] p-4 font-mono text-sm text-gray-900 bg-white resize-none focus:outline-none"
                    spellCheck={false}
                    placeholder="Select a prompt to edit..."
                  />
                </div>
              )}
            </div>

            {/* Info */}
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">How it works</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Changes are saved to YAML files in apps/ai-core/prompts/</li>
                <li>• Hot-reload: Changes take effect immediately without restarting the server</li>
                <li>• YAML syntax is validated before saving</li>
                <li>• All prompts are version-controlled with Git</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
