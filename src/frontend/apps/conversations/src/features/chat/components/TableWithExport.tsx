import { memo, useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, Icon, Text } from '@/components';
import { useFeatureFlags } from '@/core/config';

import { exportTableToCSV, parseHtmlTable } from '../utils/exportTable';

const LONG_TEXT_THRESHOLD = 50;
const LONG_TEXT_MIN_WIDTH = '300px';

interface TableWithExportProps {
  children: ReactNode;
}

export const TableWithExport = memo(
  ({ children, ...props }: TableWithExportProps) => {
    const { t } = useTranslation();
    const tableRef = useRef<HTMLTableElement>(null);
    const sizingTimeoutRef = useRef<ReturnType<typeof setTimeout>>(undefined);
    const featureFlags = useFeatureFlags();

    useEffect(() => {
      if (!tableRef.current) {
        return;
      }

      if (sizingTimeoutRef.current) {
        clearTimeout(sizingTimeoutRef.current);
      }

      sizingTimeoutRef.current = setTimeout(() => {
        if (!tableRef.current) {
          return;
        }
        const cells = tableRef.current.querySelectorAll('td, th');
        cells.forEach((cell) => {
          const textContent = cell.textContent || '';
          if (textContent.length > LONG_TEXT_THRESHOLD) {
            (cell as HTMLElement).style.minWidth = LONG_TEXT_MIN_WIDTH;
          }
        });
      }, 500);

      return () => {
        if (sizingTimeoutRef.current) {
          clearTimeout(sizingTimeoutRef.current);
        }
      };
    }, [children]);

    const handleExport = () => {
      if (!tableRef.current) {
        return;
      }

      const tableData = parseHtmlTable(tableRef.current);
      const filename = `tableau_${new Date().toISOString().slice(0, 10)}`;
      exportTableToCSV(tableData, filename);
    };

    return (
      <Box
        $position="relative"
        $css={css`
          margin: 16px 0;
        `}
      >
        {/* Export button - only visible if feature is enabled */}
        {featureFlags.enable_table_export && (
          <Box
            $css={css`
              position: absolute;
              top: -20px;
              right: 0;
              z-index: 10;
            `}
          >
            <Box
              as="button"
              onClick={handleExport}
              $css={css`
                display: flex;
                align-items: center;
                gap: 4px;
                padding: 4px 8px;
                background: var(--c--theme--colors--greyscale-700);
                border: 1px solid var(--c--theme--colors--greyscale-750);
                border-radius: 6px;
                cursor: pointer;
                font-size: 12px;
                color: white;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
                transition: all 0.15s ease;

                &:hover {
                  background: var(--c--theme--colors--greyscale-800);
                  border-color: var(--c--theme--colors--greyscale-850);
                }
              `}
            >
              <Icon
                iconName="download"
                $size="14px"
                $css="font-family: 'Material Symbols Outlined' !important; color: white !important;"
              />
              <Text $size="xs" $css="color: white !important;">
                {t('Export CSV')}
              </Text>
            </Box>
          </Box>
        )}

        {/* Table wrapper with horizontal scroll */}
        <Box
          $css={css`
            overflow-x: auto;
            max-width: 100%;
          `}
        >
          <table ref={tableRef} {...props}>
            {children}
          </table>
        </Box>
      </Box>
    );
  },
);

TableWithExport.displayName = 'TableWithExport';
