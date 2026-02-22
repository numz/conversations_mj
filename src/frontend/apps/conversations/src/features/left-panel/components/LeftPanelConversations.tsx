import { useRouter } from 'next/router';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';

import { Box, InfiniteScroll, Text } from '@/components';
import { useFeatureFlags } from '@/core/config/api/useFeatureFlags';
import { useCunninghamTheme } from '@/cunningham';
import { useInfiniteConversations } from '@/features/chat/api/useConversations';
import { ConversationGroupHeader } from '@/features/left-panel/components/ConversationGroupHeader';
import { LeftPanelConversationItem } from '@/features/left-panel/components/LeftPanelConversationItem';
import { groupConversationsByDate } from '@/features/left-panel/utils/groupConversationsByDate';

export const LeftPanelConversations = () => {
  const { t } = useTranslation();
  const router = useRouter();
  const { id } = router.query;

  const { spacingsTokens } = useCunninghamTheme();
  const featureFlags = useFeatureFlags();

  const conversations = useInfiniteConversations({
    page: 1,
    ordering: '-updated_at',
  });

  const allConversations = useMemo(
    () => conversations.data?.pages.flatMap((page) => page.results) || [],
    [conversations.data?.pages],
  );

  const groupedConversations = useMemo(
    () => groupConversationsByDate(allConversations),
    [allConversations],
  );

  if (allConversations.length === 0) {
    return null;
  }

  return (
    <Box>
      <Box
        $padding={{ horizontal: 'xs' }}
        $gap={spacingsTokens['2xs']}
        $height="50vh"
        data-testid="left-panel-favorites"
      >
        <Text
          $size="sm"
          $variation="700"
          $padding={{ horizontal: 'xs' }}
          $weight="700"
        >
          {t('History')}
        </Text>
        <InfiniteScroll
          hasMore={conversations.hasNextPage}
          isLoading={conversations.isFetchingNextPage}
          next={() => void conversations.fetchNextPage()}
        >
          {featureFlags.conversation_grouping_enabled
            ? groupedConversations.map((group) => (
                <Box key={group.group}>
                  <ConversationGroupHeader
                    group={group.group}
                    count={group.conversations.length}
                  />
                  {group.conversations.map((conversation) => (
                    <LeftPanelConversationItem
                      key={conversation.id}
                      isCurrentConversation={conversation.id === id}
                      conversation={conversation}
                    />
                  ))}
                </Box>
              ))
            : allConversations.map((conversation) => (
                <LeftPanelConversationItem
                  key={conversation.id}
                  isCurrentConversation={conversation.id === id}
                  conversation={conversation}
                />
              ))}
        </InfiniteScroll>
      </Box>
    </Box>
  );
};
