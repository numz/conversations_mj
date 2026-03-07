import { renderHook } from '@testing-library/react';

import { useFeatureFlags } from '../useFeatureFlags';

// Mock useConfig
const mockUseConfig = jest.fn();
jest.mock('../useConfig', () => ({
  useConfig: () => mockUseConfig(),
}));

describe('useFeatureFlags', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('returns feature_flags_custom from config', () => {
    mockUseConfig.mockReturnValue({
      data: {
        feature_flags_custom: {
          CODE_DOWNLOAD_ENABLED: true,
          REASONING_BOX_ENABLED: false,
        },
      },
    });

    const { result } = renderHook(() => useFeatureFlags());

    expect(result.current).toEqual({
      CODE_DOWNLOAD_ENABLED: true,
      REASONING_BOX_ENABLED: false,
    });
  });

  it('returns empty object when config is undefined', () => {
    mockUseConfig.mockReturnValue({ data: undefined });

    const { result } = renderHook(() => useFeatureFlags());

    expect(result.current).toEqual({});
  });

  it('returns empty object when feature_flags_custom is missing', () => {
    mockUseConfig.mockReturnValue({
      data: { ENVIRONMENT: 'test' },
    });

    const { result } = renderHook(() => useFeatureFlags());

    expect(result.current).toEqual({});
  });

  it('returns empty object when config data is null', () => {
    mockUseConfig.mockReturnValue({ data: null });

    const { result } = renderHook(() => useFeatureFlags());

    expect(result.current).toEqual({});
  });
});
