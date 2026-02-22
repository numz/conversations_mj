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
  usage?: ExtendedUsage;
};

export interface ChatConversation {
  id: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
  title?: string;
}
