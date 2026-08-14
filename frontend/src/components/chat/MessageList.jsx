import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import BrandIcon from '../shared/BrandIcon';
import Icon from '../shared/Icon';

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
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3"></div>
        <p className="text-xs font-medium text-text-muted">Loading research history...</p>
      </div>
    );
  }

  if (messages.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[70vh] text-center px-4 max-w-2xl mx-auto select-none">
        {/* Subtle Ambient Brand Glow */}
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse"></div>
          <div className="relative w-14 h-14 rounded-2xl bg-surface-elevated border border-primary-border flex items-center justify-center shadow-[0_0_24px_rgba(99,102,241,0.25)]">
            <BrandIcon size={28} />
          </div>
        </div>

        <h2 className="text-xl md:text-2xl font-semibold text-text mb-2 tracking-tight">
          What would you like to uncover?
        </h2>
        <p className="text-xs md:text-sm text-text-muted max-w-md mb-8 leading-relaxed">
          KueryCore uses Hybrid Search (Vector + BM25) and Vision OCR to deliver grounded answers with strict citation fidelity.
        </p>

        {/* Suggestion Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full text-left">
          {[
            {
              title: 'Architectural Synthesis',
              prompt: 'Summarize the key architectural decisions and system design tradeoffs in the uploaded documents.',
            },
            {
              title: 'Requirement Extraction',
              prompt: 'Extract all functional constraints, performance metrics, and deadlines mentioned in the corpus.',
            },
            {
              title: 'Security & Compliance',
              prompt: 'Review the documents for any compliance standards, encryption guidelines, or security policies.',
            },
            {
              title: 'Entity Cross-Reference',
              prompt: 'Identify key stakeholders, project roles, and referenced external services across all sections.',
            },
          ].map((suggestion) => (
            <button
              key={suggestion.title}
              type="button"
              onClick={() => onSendMessage && onSendMessage(suggestion.prompt)}
              className="group p-3.5 rounded-xl bg-surface/60 hover:bg-surface border border-border hover:border-border-strong text-left transition-all duration-150 tactile-btn cursor-pointer shadow-sm"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-semibold text-text-secondary group-hover:text-text">
                  {suggestion.title}
                </span>
                <Icon name="send" size={12} className="text-text-muted group-hover:text-primary-light transition-transform group-hover:translate-x-0.5" />
              </div>
              <p className="text-[11px] text-text-muted line-clamp-2 leading-normal">
                "{suggestion.prompt}"
              </p>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-6 max-w-3xl mx-auto w-full pb-6">
      {messages.map((msg, idx) => (
        <MessageBubble
          key={idx}
          message={msg}
          onCitationClick={onCitationClick}
        />
      ))}

      {isGenerating && (
        <div className="flex w-full justify-start animate-in fade-in duration-200">
          <div className="rounded-2xl px-4 py-3 bg-surface border border-border text-text shadow-sm flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></span>
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:150ms]"></span>
              <span className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:300ms]"></span>
            </div>
            <span className="text-xs text-text-muted font-medium">Retrieving citations &amp; generating response...</span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}