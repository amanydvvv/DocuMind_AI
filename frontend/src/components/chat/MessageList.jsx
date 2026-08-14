import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import BrandIcon from '../shared/BrandIcon';

export default function MessageList({
  messages,
  isLoadingHistory,
  isGenerating,
  onCitationClick,
  onSendMessage,
}) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  if (isLoadingHistory) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center">
        <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-sm font-medium text-text-muted">Loading conversation history...</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8 mt-12">
        <div className="w-16 h-16 bg-primary-soft rounded-2xl flex items-center justify-center mb-4 shadow-sm">
          <BrandIcon size={32} />
        </div>
        <h2 className="text-2xl font-bold text-text mb-2">KueryCore AI Assistant</h2>
        <p className="text-text-muted max-w-md text-sm mb-6">
          Ask questions about your uploaded documents or start a new research thread.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-lg w-full text-left">
          {[
            {
              icon: '💡',
              label: (
                <>
                  <strong className="text-text">Synthesize:</strong> "Summarize the
                  key architectural decisions in the document."
                </>
              ),
              prompt: 'Summarize the key architectural decisions in the document.',
            },
            {
              icon: '🔍',
              label: (
                <>
                  <strong className="text-text">Extract:</strong> "Who is the project
                  lead and what is the target completion date?"
                </>
              ),
              prompt:
                'Who is the project lead and what is the target completion date?',
            },
          ].map((suggestion) => (
            <button
              key={suggestion.prompt}
              type="button"
              onClick={() => onSendMessage && onSendMessage(suggestion.prompt)}
              className="p-3.5 bg-surface border border-border rounded-xl text-xs text-text-muted hover:border-primary hover:bg-primary-soft transition-colors text-left cursor-pointer"
            >
              {suggestion.icon} {suggestion.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-4 max-w-4xl mx-auto w-full">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          message={msg}
          onCitationClick={onCitationClick}
        />
      ))}

      {isGenerating && (
        <div className="flex w-full justify-start mb-6">
          <div className="max-w-[80%] rounded-2xl px-5 py-4 bg-surface border border-border text-text rounded-bl-sm shadow-sm flex items-center gap-2">
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-100"></div>
            <div className="w-2 h-2 bg-primary rounded-full animate-bounce delay-200"></div>
            <span className="text-sm text-text-muted ml-2 font-medium">Searching knowledge base...</span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}