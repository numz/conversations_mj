import React from 'react';

import { Box, StyledLink } from '@/components';

const styles: Record<string, React.CSSProperties> = {
  title: {
    color: 'var(--c--contextuals--content--semantic--neutral--primary)',
    fontWeight: '500',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: 'block',
  },
};

/**
 * Extract a meaningful title from a URL when no title is provided.
 */
const extractTitleFromUrl = (url: string): string => {
  try {
    const urlObj = new URL(url);
    const hostname = urlObj.hostname;
    const pathname = urlObj.pathname;

    // Wikipedia: extract article title
    if (hostname.includes('wikipedia.org')) {
      const wikiTitle = pathname.split('/wiki/')[1];
      if (wikiTitle) {
        return decodeURIComponent(wikiTitle.replace(/_/g, ' '));
      }
    }

    // Cour de cassation / Judilibre
    if (
      hostname.includes('courdecassation.fr') ||
      hostname.includes('judilibre')
    ) {
      return 'Cour de cassation';
    }

    // Legifrance
    if (hostname.includes('legifrance.gouv.fr')) {
      return 'Légifrance';
    }

    // Generic: try to get last meaningful path segment
    const segments = pathname.split('/').filter(Boolean);
    if (segments.length > 0) {
      const lastSegment = segments[segments.length - 1];
      const cleanSegment = decodeURIComponent(
        lastSegment.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' '),
      );
      if (cleanSegment.length > 3 && cleanSegment.length < 100) {
        return cleanSegment;
      }
    }

    return hostname;
  } catch {
    return url;
  }
};

interface SourceItemProps {
  url: string;
  title?: string | null;
}

export const SourceItem: React.FC<SourceItemProps> = ({
  url,
  title: backendTitle,
}) => {
  const displayTitle = backendTitle || extractTitleFromUrl(url);

  return (
    <Box $direction="row" $gap="4px" $align="center">
      <Box
        $direction="row"
        $align="start"
        $css="font-size: 14px;"
        $width="100%"
      >
        {url.startsWith('http') ? (
          <StyledLink
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            $css={`
                display: flex;
                align-items: center;
                gap: 0.4rem;
                border-radius: 4px;
                padding: 4px;
                width: 100%;
                text-decoration: none;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
                background-color: transparent;
                transition: background-color 0.3s;
                color: var(--c--contextuals--content--semantic--neutral--tertiary);
                &:hover {
                  color: var(--c--contextuals--content--semantic--neutral--tertiary);
                  background-color: var(--c--contextuals--background--semantic--neutral--tertiary);
                }
            `}
          >
            <Box>🔗</Box>
            <Box
              $padding={{ right: '4px' }}
              $align="center"
              style={styles.title}
            >
              {displayTitle}
            </Box>
          </StyledLink>
        ) : (
          <Box>{url}</Box>
        )}
      </Box>
    </Box>
  );
};
