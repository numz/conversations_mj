import { Message } from '@ai-sdk/react';

export type ChatMessage = Message & {
  feedback?: 'positive' | 'negative' | null;
};

export interface ChatConversation {
  id: string;
  messages: ChatMessage[];
  message_feedbacks?: Record<
    string,
    { value: 'positive' | 'negative'; comment?: string }
  >;
  created_at: string;
  updated_at: string;
  title?: string;
}
