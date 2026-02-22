import { UseChatOptions, useChat as useAiSdkChat } from '@ai-sdk/react';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';

import { fetchAPI } from '@/api';
import { KEY_LIST_CONVERSATION } from '@/features/chat/api/useConversations';
import { useChatPreferencesStore } from '@/features/chat/stores/useChatPreferencesStore';

import {
  ExtendedUsage,
  ExtendedUsageAnnotation,
} from '../types';

const fetchAPIAdapter = (input: RequestInfo | URL, init?: RequestInit) => {
  let url: string;
  if (typeof input === 'string') {
    url = input;
  } else if (input instanceof URL) {
    url = input.toString();
  } else if (input instanceof Request) {
    url = input.url;
  } else {
    throw new Error('Unsupported input type for fetchAPIAdapter');
  }

  const searchParams = new URLSearchParams();

  const { forceWebSearch, selectedModelHrid } =
    useChatPreferencesStore.getState();

  if (forceWebSearch) {
    searchParams.append('force_web_search', 'true');
  }

  if (selectedModelHrid) {
    searchParams.append('model_hrid', selectedModelHrid);
  }

  if (searchParams.toString()) {
    const separator = url.includes('?') ? '&' : '?';
    url = `${url}${separator}${searchParams.toString()}`;
  }

  return fetchAPI(url, init);
};

interface ConversationMetadataEvent {
  type: 'conversation_metadata';
  conversationId: string;
  title: string;
}
// Type guard to check if an item is a ConversationMetadataEvent
function isConversationMetadataEvent(
  item: unknown,
): item is ConversationMetadataEvent {
  return (
    typeof item === 'object' &&
    item !== null &&
    'type' in item &&
    item.type === 'conversation_metadata' &&
    'conversationId' in item &&
    typeof item.conversationId === 'string' &&
    'title' in item &&
    typeof item.title === 'string'
  );
}

export type UseChatResult = ReturnType<typeof useAiSdkChat> & {
  usageByMessageId: Map<string, ExtendedUsage>;
};

export function useChat(
  options: Omit<UseChatOptions, 'fetch'>,
): UseChatResult {
  const queryClient = useQueryClient();

  const [usageByMessageId, setUsageByMessageId] = useState<
    Map<string, ExtendedUsage>
  >(() => new Map());

  const { onFinish: userOnFinish, ...restOptions } = options;

  const handleFinish = useCallback(
    (
      message: Parameters<NonNullable<UseChatOptions['onFinish']>>[0],
      finishOptions: Parameters<NonNullable<UseChatOptions['onFinish']>>[1],
    ) => {
      // Extract extended usage from message annotations
      const annotations = message.annotations as
        | ExtendedUsageAnnotation[]
        | undefined;
      const extendedUsageAnnotation = annotations?.find(
        (a) => a?.type === 'extended_usage',
      );

      const extendedUsage: ExtendedUsage = {
        prompt_tokens:
          extendedUsageAnnotation?.prompt_tokens ??
          finishOptions?.usage?.promptTokens ??
          0,
        completion_tokens:
          extendedUsageAnnotation?.completion_tokens ??
          finishOptions?.usage?.completionTokens ??
          0,
        cost: extendedUsageAnnotation?.cost,
        carbon: extendedUsageAnnotation?.carbon,
        latency_ms: extendedUsageAnnotation?.latency_ms,
      };

      if (message.id) {
        setUsageByMessageId((prev) =>
          new Map(prev).set(message.id, extendedUsage),
        );
      }

      userOnFinish?.(message, finishOptions);
    },
    [userOnFinish],
  );

  const result = useAiSdkChat({
    ...restOptions,
    maxSteps: 3,
    fetch: fetchAPIAdapter,
    onFinish: handleFinish,
  });

  useEffect(() => {
    if (result.data && Array.isArray(result.data)) {
      for (const item of result.data) {
        if (isConversationMetadataEvent(item)) {
          void queryClient.invalidateQueries({
            queryKey: [KEY_LIST_CONVERSATION],
          });
        }
      }
    }
  }, [result.data, queryClient]);

  return {
    ...result,
    usageByMessageId,
  };
}
