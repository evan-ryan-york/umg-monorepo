'use client';

import { useEffect, useRef, useState } from 'react';
import { useMentorChat } from '@/hooks/useMentorChat';
import ChatMessage from '@/components/ChatMessage';

export default function ChatPage(): React.JSX.Element {
  const { messages, isLoading, error, sendMessage, clearHistory } = useMentorChat();
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const messageToSend = input;
    setInput(''); // Clear immediately for better UX
    await sendMessage(messageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chat with Mentor</h1>
          <p className="text-sm text-gray-600">
            Your strategic thinking partner, grounded in your knowledge graph
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Clear History
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="max-w-md">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                Start a conversation
              </h2>
              <p className="text-gray-600 mb-6">
                Share reflections, ask questions, or explore your work. Everything you discuss
                feeds into your knowledge graph and helps the Mentor understand you better.
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 text-left">
                <p className="text-sm text-gray-700 mb-2 font-medium">Try asking:</p>
                <ul className="text-sm text-gray-600 space-y-1">
                  <li>• &ldquo;What should I focus on today?&rdquo;</li>
                  <li>• &ldquo;Tell me about my recent work&rdquo;</li>
                  <li>• &ldquo;What patterns do you see in my goals?&rdquo;</li>
                </ul>
              </div>
            </div>
          </div>
        ) : (
          <>
            {messages.map((msg, idx) => (
              <ChatMessage
                key={`${msg.timestamp}-${idx}`}
                role={msg.role}
                content={msg.content}
                entities={msg.entities}
                timestamp={msg.timestamp}
              />
            ))}

            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="max-w-[80%] mr-auto">
                  <div className="rounded-lg p-4 bg-gray-50 border-2 border-gray-200">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
                      </div>
                      <span className="text-sm text-gray-600">Mentor is thinking...</span>
                    </div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Error Display */}
      {error && (
        <div className="px-6 py-3 bg-red-50 border-t border-red-200">
          <p className="text-sm text-red-800">
            <strong>Error:</strong> {error}
          </p>
        </div>
      )}

      {/* Input */}
      <div className="bg-white border-t border-gray-200 px-6 py-4">
        <form onSubmit={handleSubmit} className="flex gap-3">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Shift+Enter for new line)"
            className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            rows={3}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Sending...' : 'Send'}
          </button>
        </form>
        <p className="text-xs text-gray-500 mt-2">
          All conversations are automatically saved to your knowledge graph
        </p>
      </div>
    </div>
  );
}
