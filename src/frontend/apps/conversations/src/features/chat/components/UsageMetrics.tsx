import { Message } from '@ai-sdk/ui-utils';
import React from 'react';

import { Box, Text } from '@/components';

interface ExtendedMetrics {
  type: 'extended_metrics';
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  latency_ms: number;
  cost?: number;
  cost_currency?: string;
  carbon_g?: number;
}

function isExtendedMetrics(value: unknown): value is ExtendedMetrics {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as Record<string, unknown>).type === 'extended_metrics'
  );
}

export function extractMetrics(
  message: Message,
): ExtendedMetrics | undefined {
  if (!message.annotations) return undefined;
  return message.annotations.find(isExtendedMetrics);
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatCost(cost: number, currency?: string): string {
  const curr = currency ?? 'USD';
  if (cost < 0.01) return `<0.01 ${curr}`;
  return `${cost.toFixed(2)} ${curr}`;
}

function formatCarbon(grams: number): string {
  if (grams < 1) return `${(grams * 1000).toFixed(1)} mgCO₂`;
  return `${grams.toFixed(2)} gCO₂`;
}

interface UsageMetricsProps {
  message: Message;
}

export const UsageMetrics: React.FC<UsageMetricsProps> = React.memo(
  ({ message }) => {
    const metrics = extractMetrics(message);
    if (!metrics) return null;

    const items: string[] = [];
    items.push(`${metrics.total_tokens} tokens`);
    items.push(formatLatency(metrics.latency_ms));
    if (metrics.cost != null) {
      items.push(formatCost(metrics.cost, metrics.cost_currency));
    }
    if (metrics.carbon_g != null) {
      items.push(formatCarbon(metrics.carbon_g));
    }

    return (
      <Box
        $direction="row"
        $gap="8px"
        $margin={{ top: 'xs' }}
        $css={`
          color: var(--c--contextuals--content--semantic--neutral--tertiary);
          font-size: 11px;
          opacity: 0.8;
        `}
      >
        {items.map((item, i) => (
          <Text key={i} $size="xs">
            {item}
          </Text>
        ))}
      </Box>
    );
  },
);

UsageMetrics.displayName = 'UsageMetrics';
