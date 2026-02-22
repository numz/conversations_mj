import { memo, useRef } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, Icon, Text } from '@/components';
import { useCunninghamTheme } from '@/cunningham';
import { useFeatureFlags } from '@/core/config';
import { useClipboard } from '@/hook';

import { exportTextToTXT } from '../utils/exportText';

interface CodeBlockActionsProps {
  onCopy: () => void;
  onDownload?: () => void;
  isDarkMode: boolean;
}

const CodeBlockActions = ({
  onCopy,
  onDownload,
  isDarkMode,
}: CodeBlockActionsProps) => {
  const { t } = useTranslation();

  const buttonCss = css`
    padding: 6px 10px;
    background: ${isDarkMode ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.03)'};
    border: 1px solid ${isDarkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(255, 255, 255, 0.15)'};
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    color: #fff;
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 4px;
    transition: all 0.2s;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    width: fit-content;
    &:hover {
      background: ${isDarkMode ? 'rgba(255, 255, 255, 0.15)' : 'rgba(255, 255, 255, 0.1)'};
      border: 1px solid ${isDarkMode ? 'rgba(255, 255, 255, 0.3)' : 'rgba(255, 255, 255, 0.2)'};
    }
  `;

  return (
    <Box
      $css={css`
        position: absolute;
        top: 8px;
        right: 8px;
        display: flex;
        flex-direction: row;
        gap: 4px;
        z-index: 10;
      `}
    >
      <Box as="button" onClick={onCopy} $css={buttonCss}>
        <Icon
          iconName="content_copy"
          $size="14px"
          $theme="greyscale"
          $variation="200"
          $css="font-family: 'Material Symbols Outlined' !important;"
        />
        <Text $size="xs" $theme="greyscale" $variation="200">
          {t('Copy code')}
        </Text>
      </Box>

      {onDownload && (
        <Box as="button" onClick={onDownload} $css={buttonCss}>
          <Icon
            iconName="download"
            $size="14px"
            $theme="greyscale"
            $variation="200"
            $css="font-family: 'Material Symbols Outlined' !important;"
          />
          <Text $size="xs" $theme="greyscale" $variation="200">
            {t('Download')}
          </Text>
        </Box>
      )}
    </Box>
  );
};

interface CodeBlockProps {
  children: ReactNode;
  style?: React.CSSProperties;
  [key: string]: unknown;
}

export const CodeBlock = memo(
  ({ children, style: propStyle, ...props }: CodeBlockProps) => {
    const preRef = useRef<HTMLPreElement>(null);
    const copyToClipboard = useClipboard();
    const featureFlags = useFeatureFlags();
    const { isDarkMode } = useCunninghamTheme();

    const getCodeContent = (): string => {
      const code = preRef.current?.querySelector('code');
      return code?.textContent || '';
    };

    const handleCopy = () => {
      void copyToClipboard(getCodeContent());
    };

    const handleDownload = () => {
      const content = getCodeContent();
      const filename = `code_${new Date().toISOString().slice(0, 10)}`;
      exportTextToTXT(content, filename);
    };

    return (
      <Box
        $position="relative"
        $css={css`
          margin: 1em 0;
        `}
      >
        <CodeBlockActions
          onCopy={handleCopy}
          isDarkMode={isDarkMode}
          onDownload={
            featureFlags.code_download_enabled ? handleDownload : undefined
          }
        />
        <Box
          $css={css`
            overflow-x: auto;
            max-width: 100%;
            border-radius: 8px;
          `}
        >
          <pre
            ref={preRef}
            {...props}
            style={{
              ...propStyle,
              whiteSpace: 'pre',
              margin: 0,
              padding: '1rem',
              backgroundColor: 'var(--c--globals--colors--gray-800)',
              width: 'max-content',
              minWidth: '100%',
              overflow: 'visible',
            }}
          >
            {children}
          </pre>
        </Box>
      </Box>
    );
  },
);

CodeBlock.displayName = 'CodeBlock';
