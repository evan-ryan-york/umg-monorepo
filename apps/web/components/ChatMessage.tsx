'use client';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  entities?: string[];
  timestamp: string;
}

export default function ChatMessage({ role, content, entities, timestamp }: ChatMessageProps): React.JSX.Element {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? 'ml-auto' : 'mr-auto'}`}>
        <div
          className={`rounded-lg p-4 ${
            isUser
              ? 'bg-blue-50 border-2 border-blue-200'
              : 'bg-gray-50 border-2 border-gray-200'
          }`}
        >
          <div className="flex items-start gap-2 mb-2">
            <span className="text-sm font-semibold text-gray-700">
              {isUser ? 'You' : 'Mentor'}
            </span>
          </div>

          <p className="text-gray-900 whitespace-pre-wrap">{content}</p>

          {entities && entities.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-1">
              {entities.map((entity, idx) => (
                <span
                  key={`${entity}-${idx}`}
                  className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded"
                >
                  {entity}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="mt-1 px-2">
          <span className="text-xs text-gray-500">
            {new Date(timestamp).toLocaleTimeString([], {
              hour: 'numeric',
              minute: '2-digit'
            })}
          </span>
        </div>
      </div>
    </div>
  );
}
