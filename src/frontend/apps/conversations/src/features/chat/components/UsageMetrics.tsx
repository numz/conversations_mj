import { useTranslation } from 'react-i18next';

import { Box, Icon, Text } from '@/components';

import { ExtendedUsage } from '../types';

interface UsageMetricsProps {
  usage: ExtendedUsage;
}

export const UsageMetrics = ({ usage }: UsageMetricsProps) => {
  const { t } = useTranslation();

  const totalTokens = usage.prompt_tokens + usage.completion_tokens;

  // Convert kgCO2eq to mgCO2eq for display (more readable for small values)
  const carbonMg =
    usage.carbon?.kgCO2eq?.max !== undefined
      ? usage.carbon.kgCO2eq.max * 1_000_000 // kg to mg
      : null;

  // Convert kWh to Wh for display
  const energyWh =
    usage.carbon?.kWh?.max !== undefined
      ? usage.carbon.kWh.max * 1000 // kWh to Wh
      : null;

  // Convert ms to seconds
  const latencySeconds =
    usage.latency_ms !== undefined ? usage.latency_ms / 1000 : null;

  // Don't render if no extended metrics available
  const hasExtendedMetrics =
    carbonMg !== null || energyWh !== null || latencySeconds !== null;

  if (!hasExtendedMetrics && totalTokens === 0) {
    return null;
  }

  return (
    <Box
      $direction="row"
      $align="center"
      $gap="8px"
      $css={`
        font-size: 11px;
        color: var(--c--theme--colors--greyscale-500);
        flex-wrap: nowrap;
        flex-shrink: 1;
        min-width: 0;
      `}
    >
      {/* Total tokens */}
      {totalTokens > 0 && (
        <Box
          $direction="row"
          $align="center"
          $gap="3px"
          title={t('Total tokens used')}
        >
          <Icon
            iconName="token"
            $theme="greyscale"
            $variation="500"
            $size="16px"
          />
          <Text $theme="greyscale" $variation="500" $size="11px">
            {totalTokens.toLocaleString()}
          </Text>
        </Box>
      )}

      {/* Carbon footprint */}
      {carbonMg !== null && (
        <Box
          $direction="row"
          $align="center"
          $gap="3px"
          title={t('Carbon footprint (estimated max)')}
        >
          <Icon
            iconName="eco"
            $theme="greyscale"
            $variation="500"
            $size="16px"
          />
          <Text $theme="greyscale" $variation="500" $size="11px">
            {carbonMg < 0.01
              ? `<0.01 mg CO2`
              : `${carbonMg.toFixed(2)} mg CO2`}
          </Text>
        </Box>
      )}

      {/* Energy consumption */}
      {energyWh !== null && (
        <Box
          $direction="row"
          $align="center"
          $gap="3px"
          title={t('Energy consumption (estimated max)')}
        >
          <Icon
            iconName="bolt"
            $theme="greyscale"
            $variation="500"
            $size="16px"
          />
          <Text $theme="greyscale" $variation="500" $size="11px">
            {energyWh < 0.001
              ? `<0.001 Wh`
              : `${energyWh.toFixed(3)} Wh`}
          </Text>
        </Box>
      )}

      {/* Latency */}
      {latencySeconds !== null && (
        <Box
          $direction="row"
          $align="center"
          $gap="3px"
          title={t('Response time')}
        >
          <Icon
            iconName="schedule"
            $theme="greyscale"
            $variation="500"
            $size="16px"
          />
          <Text $theme="greyscale" $variation="500" $size="11px">
            {latencySeconds.toFixed(1)}s
          </Text>
        </Box>
      )}
    </Box>
  );
};
