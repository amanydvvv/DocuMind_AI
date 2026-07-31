export * from '../services/api';
import { sendChatMessage } from '../services/api';

export async function sendChatQuery(query, conversationId = null, documentId = null) {
  return sendChatMessage({
    question: query,
    conversation_id: conversationId,
    document_id: documentId
  });
}
