import { useState, useRef, useEffect } from 'react';
import ChatInput from './ChatInput';
import MessageBubble from './MessageBubble';
import CitationViewer from '../shared/CitationViewer';
import { sendChatQuery } from '../../lib/api';

export default function ChatInterface() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeCitation, setActiveCitation] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (query) => {
    // Optimistic UI update
    const userMessage = { role: 'user', content: query };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Send to backend
      const response = await sendChatQuery(query, conversationId);
      
      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id);
      }
      
      const aiMessage = { 
        role: 'ai', 
        content: response.answer,
        citations: response.citations // Fixed from 'sources' to 'citations'
      };
      
      setMessages(prev => [...prev, aiMessage]);
    } catch (error) {
      setMessages(prev => [...prev, { 
        role: 'ai', 
        content: `**Error:** ${error.message}` 
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50 relative">
      {/* Header */}
      <div className="bg-white border-b border-border p-4 flex items-center shadow-sm z-10">
        <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-indigo-600">
          DocuMind Chat
        </h1>
        <span className="ml-3 px-2 py-1 bg-gray-100 text-gray-500 text-xs font-medium rounded-full">
          All Documents Context
        </span>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8">
        <div className="max-w-4xl mx-auto flex flex-col">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center mt-20">
              <div className="w-16 h-16 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center text-3xl mb-4 shadow-sm">
                🤖
              </div>
              <h2 className="text-2xl font-bold text-gray-800 mb-2">Welcome to DocuMind AI</h2>
              <p className="text-gray-500 max-w-md">
                Upload your technical documents in the sidebar, then ask me anything about them.
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble 
                key={idx} 
                message={msg} 
                onCitationClick={setActiveCitation}
              />
            ))
          )}
          
          {isLoading && (
            <div className="flex w-full justify-start mb-6">
              <div className="max-w-[80%] rounded-2xl px-5 py-4 bg-white border border-border text-text rounded-bl-sm shadow-sm flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-100"></div>
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce delay-200"></div>
                <span className="text-sm text-gray-500 ml-2 font-medium">Searching knowledge base...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-white">
        <ChatInput onSendMessage={handleSendMessage} disabled={isLoading} />
      </div>

      {/* Citation Modal overlay */}
      {activeCitation && (
        <CitationViewer 
          citation={activeCitation} 
          onClose={() => setActiveCitation(null)} 
        />
      )}
    </div>
  );
}
