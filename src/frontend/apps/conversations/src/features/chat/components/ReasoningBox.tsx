import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { Box, Icon, Text } from '@/components';
import { Loader } from '@/components/Loader';
import { useFeatureFlags } from '@/core/config/api';

interface ReasoningBoxProps {
  reasoning: string;
  isStreaming: boolean;
  /** Label to show during processing (e.g., "Thinking..."). When set, replaces the header icon and "Reasoning" text */
  processingLabel?: string | null;
}

/**
 * Collapsible reasoning/thinking box component.
 * - Shows reasoning content with max-height and scrollbar
 * - Collapsible with smooth transition
 * - When collapsed, shows only the last line
 * - Auto-collapses when streaming ends
 */
export const ReasoningBox = ({
  reasoning,
  isStreaming,
  processingLabel,
}: ReasoningBoxProps) => {
  const { t } = useTranslation();
  const featureFlags = useFeatureFlags();
  const isProcessing = Boolean(processingLabel);
  const [isExpanded, setIsExpanded] = useState(false);
  const [hasAutoCollapsed, setHasAutoCollapsed] = useState(false);
  const hasContent = Boolean(reasoning);

  // Get the last line of reasoning for collapsed preview
  const lastLine = useMemo(() => {
    const lines = reasoning.trim().split('\n').filter(Boolean);
    const last = lines[lines.length - 1] || '';
    return last.length > 100 ? last.substring(0, 100) + '...' : last;
  }, [reasoning]);

  // Auto-collapse when streaming ends
  useEffect(() => {
    if (!isStreaming && !hasAutoCollapsed && reasoning) {
      const timer = setTimeout(() => {
        setIsExpanded(false);
        setHasAutoCollapsed(true);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [isStreaming, hasAutoCollapsed, reasoning]);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // Don't render if feature is disabled
  if (featureFlags.reasoning_box_enabled === false) {
    return null;
  }

  // Don't render if no reasoning content AND not processing
  if (!reasoning && !isProcessing) {
    return null;
  }

  return (
    <Box className="reasoning-container">
      {/* Header - always visible */}
      <Box
        className="reasoning-header"
        $direction="row"
        $align="center"
        $justify="space-between"
        $padding={{ horizontal: 'sm', vertical: 'xs' }}
        $background="var(--c--theme--colors--greyscale-100)"
        $radius={hasContent && isExpanded ? 'md md 0 0' : 'md'}
        $css={`
          cursor: ${hasContent ? 'pointer' : 'default'};
          user-select: none;
          border-bottom: ${hasContent && isExpanded ? '1px solid var(--c--theme--colors--greyscale-200)' : 'none'};
          transition: border-radius 0.3s ease;
        `}
        onClick={hasContent ? toggleExpanded : undefined}
        onKeyDown={
          hasContent
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleExpanded();
                }
              }
            : undefined
        }
        role={hasContent ? 'button' : undefined}
        tabIndex={hasContent ? 0 : undefined}
        aria-expanded={hasContent ? isExpanded : undefined}
        aria-controls={hasContent ? 'reasoning-content' : undefined}
      >
        <Box $direction="row" $align="center" $gap="8px">
          {isProcessing ? (
            <>
              <Box $css="display: flex; align-items: center; transform: scale(0.7);">
                <Loader />
              </Box>
              <Text
                $variation="600"
                $css="font-size: 0.85em; font-weight: 500;"
              >
                {processingLabel}
              </Text>
            </>
          ) : (
            <>
              <Icon
                iconName="psychology"
                $theme="greyscale"
                $variation="500"
                $size="16px"
              />
              <Text
                $theme="greyscale"
                $variation="500"
                $css="font-size: 0.85em; font-weight: 500;"
              >
                {t('Reasoning')}
              </Text>
              {isStreaming && (
                <Box
                  className="reasoning-streaming-indicator"
                  $css={`
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: var(--c--theme--colors--primary-500);
                  `}
                />
              )}
            </>
          )}
        </Box>
        {hasContent && (
          <Box $direction="row" $align="center" $gap="4px">
            {!isExpanded && lastLine && (
              <Text
                $theme="greyscale"
                $variation="400"
                $css={`
                  font-size: 0.8em;
                  max-width: 200px;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                `}
              >
                {lastLine}
              </Text>
            )}
            <Icon
              iconName={isExpanded ? 'expand_less' : 'expand_more'}
              $theme="greyscale"
              $variation="500"
              $size="18px"
              $css="transition: transform 0.3s ease;"
            />
          </Box>
        )}
      </Box>

      {/* Content - collapsible */}
      {hasContent && (
        <Box
          id="reasoning-content"
          className={`reasoning-content ${isExpanded ? 'expanded' : 'collapsed'}`}
          $background="var(--c--theme--colors--greyscale-100)"
          $color="var(--c--theme--colors--greyscale-500)"
          $padding={{ horizontal: 'sm', bottom: 'sm', top: 'xs' }}
          $radius="0 0 md md"
          $css={`
            font-size: 0.85em;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: ${isExpanded ? '300px' : '0'};
            overflow-y: ${isExpanded ? 'auto' : 'hidden'};
            opacity: ${isExpanded ? '1' : '0'};
            padding-top: ${isExpanded ? 'var(--c--theme--spacings--xs)' : '0'};
            padding-bottom: ${isExpanded ? 'var(--c--theme--spacings--sm)' : '0'};
            transition: max-height 0.3s ease, opacity 0.2s ease, padding 0.3s ease;
          `}
        >
          {reasoning}
        </Box>
      )}
    </Box>
  );
};
