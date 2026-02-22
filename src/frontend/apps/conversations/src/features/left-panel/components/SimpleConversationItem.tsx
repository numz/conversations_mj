import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, Text } from '@/components';
import { useFeatureFlags } from '@/core/config/api/useFeatureFlags';
import { useCunninghamTheme } from '@/cunningham';
import { ChatConversation } from '@/features/chat/types';
import { useTypewriter } from '@/features/left-panel/hooks/useTypewriter';
import { formatRelativeTime } from '@/features/left-panel/utils/groupConversationsByDate';

import BubbleIcon from '../assets/bubble-bold.svg';

const ItemTextCss = css`
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: initial;
  display: -webkit-box;
  line-clamp: 1;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
`;
const bubbleContainerStyles = css`
  background-color: transparent;
  filter: drop-shadow(0px 2px 2px rgba(0, 0, 0, 0.05));
  flex-shrink: 0;
`;
type SimpleConversationItemProps = {
  conversation: ChatConversation;
  showAccesses?: boolean;
  isCurrentConversation?: boolean;
};

export const SimpleConversationItem = memo(function SimpleConversationItem({
  conversation,
  showAccesses: _showAccesses = false,
  isCurrentConversation = false,
}: SimpleConversationItemProps) {
  const { t, i18n } = useTranslation();
  const { spacingsTokens } = useCunninghamTheme();
  const featureFlags = useFeatureFlags();

  const titleText = conversation.title || t('Untitled conversation');
  const animatedTitle = useTypewriter(
    titleText,
    conversation.id,
    25,
    isCurrentConversation,
  );
  const title =
    featureFlags.inline_rename_enabled && isCurrentConversation
      ? animatedTitle
      : titleText;

  return (
    <Box
      $direction="row"
      $gap={spacingsTokens.sm}
      $overflow="auto"
      $align="center"
      className="--docs--simple-doc-item"
    >
      <Box
        $direction="row"
        $align="center"
        $css={bubbleContainerStyles}
        $padding={`${spacingsTokens['3xs']} 0`}
      >
        <BubbleIcon aria-label={t('Simple chat icon')} color="brand" />
      </Box>
      <Box
        $justify="center"
        $overflow="auto"
        $gap="2px"
        $css="flex: 1; min-width: 0;"
      >
        <Text
          aria-describedby="doc-title"
          aria-label={titleText}
          $size="sm"
          $variation="850"
          $css={ItemTextCss}
        >
          {title}
        </Text>
        {featureFlags.conversation_grouping_enabled && (
          <Text
            $size="xs"
            $css={css`
              color: var(--c--theme--colors--greyscale-400);
              font-weight: 400;
            `}
          >
            {formatRelativeTime(conversation.updated_at, i18n.language)}
          </Text>
        )}
      </Box>
    </Box>
  );
});
