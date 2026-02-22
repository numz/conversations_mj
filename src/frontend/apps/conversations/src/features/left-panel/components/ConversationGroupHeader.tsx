import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, Text } from '@/components';
import {
  TimeGroup,
  getTimeGroupLabel,
} from '@/features/left-panel/utils/groupConversationsByDate';

interface ConversationGroupHeaderProps {
  group: TimeGroup;
  count: number;
}

export const ConversationGroupHeader = ({
  group,
  count,
}: ConversationGroupHeaderProps) => {
  const { t } = useTranslation();
  const label = getTimeGroupLabel(group);

  return (
    <Box
      $direction="row"
      $align="center"
      $justify="space-between"
      $padding={{ horizontal: 'sm', vertical: 'xs' }}
      $margin={{ top: group === 'today' ? '0' : 'xs' }}
      $css={css`
        user-select: none;
      `}
    >
      <Text
        $size="xs"
        $variation="500"
        $weight="600"
        $css={css`
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: var(--c--theme--colors--greyscale-500);
        `}
      >
        {t(label)}
      </Text>
      <Text
        $size="xs"
        $variation="400"
        $css={css`
          color: var(--c--theme--colors--greyscale-400);
        `}
      >
        {count}
      </Text>
    </Box>
  );
};
