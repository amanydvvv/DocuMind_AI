import { useState } from 'react';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import CitationViewer from '../shared/CitationViewer';

export default function ChatContainer({
  activeConversation,
  messages,
  isLoadingHistory,
  isGenerating,
  error,
  onSendMessage,
}) {
  const [activeCitation, setActiveCitation] = useState(null);

  return (
    <div className="flex flex-col h-full bg-gray-50 relative overflow-hidden">
      {/* Header */}
      <div className="bg-white border-b border-border p-4 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600 truncate max-w-md">
            {activeConversation?.title || 'New Chat Session'}
          </h1>
          <span className="px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full border border-blue-100">
            {activeConversation ? 'Persisted Thread' : 'New Session'}
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 text-red-700 px-4 py-2 text-xs flex justify-between items-center">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <MessageList
          messages={messages}
          isLoadingHistory={isLoadingHistory}
          isGenerating={isGenerating}
          onCitationClick={setActiveCitation}
        />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-border">
        <ChatInput onSendMessage={onSendMessage} disabled={isGenerating || isLoadingHistory} />
      </div>

      {/* Citation Modal Overlay */}
      {activeCitation && (
        <CitationViewer
          citation={activeCitation}
          onClose={() => setActiveCitation(null)}
        />
      )}
    </div>
  );
}
