import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, Icon, Text } from '@/components';
import { PromptSuggestion, useConfig } from '@/core/config/api/useConfig';
import { useCunninghamTheme } from '@/cunningham/useCunninghamTheme';

interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
}

// Default suggestions used as fallback when config is not available
const getDefaultSuggestions = (
  t: (key: string) => string,
): PromptSuggestion[] => [
  {
    icon: 'gavel',
    title: t('Legal article'),
    prompt: t('What does article 1240 of the Civil Code say?'),
  },
  {
    icon: 'description',
    title: t('Summarize a document'),
    prompt: t('Summarize the main points of a legal document'),
  },
  {
    icon: 'balance',
    title: t('Jurisprudence'),
    prompt: t('Find recent case law on wrongful dismissal'),
  },
  {
    icon: 'edit_note',
    title: t('Draft a document'),
    prompt: t('Help me draft a formal notice letter'),
  },
  {
    icon: 'help_outline',
    title: t('Legal procedure'),
    prompt: t('What are the steps for an appeal procedure?'),
  },
  {
    icon: 'search',
    title: t('Legal research'),
    prompt: t('What are the conditions for legitimate defense?'),
  },
];

export const PromptSuggestions = ({ onSelect }: PromptSuggestionsProps) => {
  const { t } = useTranslation();
  const { data: config } = useConfig();
  const { isDarkMode } = useCunninghamTheme();

  // Use configured suggestions if available, otherwise use translated defaults
  const suggestions = useMemo(() => {
    if (config?.prompt_suggestions && config.prompt_suggestions.length > 0) {
      return config.prompt_suggestions;
    }
    return getDefaultSuggestions(t);
  }, [config?.prompt_suggestions, t]);

  return (
    <Box
      $direction="row"
      $wrap="wrap"
      $gap="12px"
      $justify="center"
      $width="100%"
      $maxWidth="750px"
      $margin={{ horizontal: 'auto', top: 'sm' }}
      $padding={{ horizontal: 'md' }}
    >
      {suggestions.map((suggestion, index) => (
        <Box
          key={index}
          onClick={() => onSelect(suggestion.prompt)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              onSelect(suggestion.prompt);
            }
          }}
          role="button"
          tabIndex={0}
          aria-label={suggestion.prompt}
          $css={css`
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
            padding: 12px 16px;
            background: var(
              --c--globals--colors--gray-${isDarkMode ? '800' : '100'}
            );
            border: 1px solid
              var(--c--globals--colors--gray-${isDarkMode ? '700' : '200'});
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            width: calc(33.333% - 8px);
            min-width: 200px;
            max-width: 240px;

            &:hover {
              background: var(
                --c--globals--colors--gray-${isDarkMode ? '750' : '150'}
              );
              border-color: var(
                --c--globals--colors--gray-${isDarkMode ? '650' : '250'}
              );
              transform: translateY(-2px);
              box-shadow: 0 4px 12px
                rgba(0, 0, 0, ${isDarkMode ? '0.25' : '0.08'});
            }

            &:focus {
              outline: 2px solid
                var(--c--globals--colors--brand-500);
              outline-offset: 2px;
            }

            &:active {
              transform: translateY(0);
            }

            @media (max-width: 768px) {
              width: calc(50% - 6px);
              min-width: 150px;
            }

            @media (max-width: 480px) {
              width: 100%;
              max-width: none;
            }
          `}
        >
          <Box $direction="row" $align="center" $gap="8px">
            <Icon
              iconName={suggestion.icon}
              $size="20px"
              $css={`color: var(--c--globals--colors--brand-${isDarkMode ? '300' : '500'});`}
            />
            <Text
              $weight="600"
              $size="sm"
              $css={`color: var(--c--globals--colors--gray-${isDarkMode ? '150' : '800'});`}
            >
              {suggestion.title}
            </Text>
          </Box>
          <Text
            $size="xs"
            $css={css`
              color: var(
                --c--globals--colors--gray-${isDarkMode ? '300' : '600'}
              );
              display: -webkit-box;
              -webkit-line-clamp: 2;
              -webkit-box-orient: vertical;
              overflow: hidden;
              text-align: left;
              line-height: 1.4;
            `}
          >
            {suggestion.prompt}
          </Text>
        </Box>
      ))}
    </Box>
  );
};
