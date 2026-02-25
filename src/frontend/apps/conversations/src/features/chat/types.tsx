import { Message } from '@ai-sdk/react';

// Extended usage metrics from OpenGateLLM
export interface CarbonRange {
  min: number;
  max: number;
}

export interface CarbonMetrics {
  kWh?: CarbonRange;
  kgCO2eq?: CarbonRange;
}

export interface ExtendedUsage {
  prompt_tokens: number;
  completion_tokens: number;
  cost?: number;
  carbon?: CarbonMetrics;
  latency_ms?: number;
}

export type ExtendedUsageAnnotation = ExtendedUsage & {
  type: 'extended_usage';
};

export type ChatMessage = Message & {
  feedback?: 'positive' | 'negative' | null;
  usage?: ExtendedUsage;
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
