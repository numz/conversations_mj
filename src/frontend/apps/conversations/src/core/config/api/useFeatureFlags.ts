import { FeatureFlagsCustom, useConfig } from './useConfig';

export function useFeatureFlags(): FeatureFlagsCustom {
  const { data: config } = useConfig();
  return config?.feature_flags_custom ?? {};
}
