import { SourceUIPart } from '@ai-sdk/ui-utils';
import React from 'react';

import { Box } from '@/components';
import { SourceItem } from '@/features/chat/components/SourceItem';

interface SourceItemListProps {
  parts: readonly SourceUIPart[];
}

const SourceItemListComponent: React.FC<SourceItemListProps> = ({ parts }) => {
  if (parts.length === 0) {
    return null;
  }

  // Deduplicate sources by URL, keeping the first occurrence
  const uniqueParts = parts.filter(
    (part, index, self) =>
      index === self.findIndex((p) => p.source.url === part.source.url),
  );

  return (
    <Box
      $direction="column"
      $padding={{ all: 'sm' }}
      $gap="4px"
      $css={`
       border: 1px solid var(--c--contextuals--border--surface--primary);
       border-radius: 8px;
       margin-top: 0.5rem;
       overflow: hidden;
     `}
    >
      {uniqueParts.map((part) => (
        <SourceItem
          key={part.source.url}
          url={part.source.url}
          title={part.source.title}
        />
      ))}
    </Box>
  );
};

SourceItemListComponent.displayName = 'SourceItemList';

export const SourceItemList = React.memo(SourceItemListComponent);
