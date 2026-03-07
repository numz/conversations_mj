import { Message } from '@ai-sdk/react';

export type CarbonRange = {
  min?: number | null;
  max?: number | null;
};

export type CarbonMetrics = {
  kWh?: CarbonRange | null;
  kgCO2eq?: CarbonRange | null;
};

export type ExtendedUsage = {
  prompt_tokens: number;
  completion_tokens: number;
  cost?: number | null;
  carbon?: CarbonMetrics | null;
  latency_ms?: number | null;
};

export type ChatMessage = Message & {
  feedback?: 'positive' | 'negative' | null;
  usage?: ExtendedUsage;
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
