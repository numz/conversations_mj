import {
  UseMutationOptions,
  useMutation,
  useQueryClient,
} from '@tanstack/react-query';

import { APIError, errorCauses, fetchAPI } from '@/api';
import { ChatConversation } from '@/features/chat/types';

import { KEY_LIST_CONVERSATION } from './useConversations';

interface UpdateConversationProps {
  conversationId: string;
  title: string;
}

export const updateConversation = async ({
  conversationId,
  title,
}: UpdateConversationProps): Promise<ChatConversation> => {
  const response = await fetchAPI(`chats/${conversationId}/`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    throw new APIError(
      'Failed to update the conversation',
      await errorCauses(response),
    );
  }

  return response.json() as Promise<ChatConversation>;
};

type UseUpdateConversationOptions = UseMutationOptions<
  ChatConversation,
  APIError,
  UpdateConversationProps
>;

export const useUpdateConversation = (
  options?: UseUpdateConversationOptions,
) => {
  const queryClient = useQueryClient();
  return useMutation<ChatConversation, APIError, UpdateConversationProps>({
    mutationFn: updateConversation,
    ...options,
    onSuccess: (data, variables, context) => {
      void queryClient.invalidateQueries({
        queryKey: [KEY_LIST_CONVERSATION],
      });
      if (options?.onSuccess) {
        void options.onSuccess(data, variables, context);
      }
    },
    onError: (error, variables, context) => {
      if (options?.onError) {
        void options.onError(error, variables, context);
      }
    },
  });
};
