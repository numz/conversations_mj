import { useQuery } from '@tanstack/react-query';
import { Resource } from 'i18next';

import { APIError, errorCauses, fetchAPI } from '@/api';
import { Theme } from '@/cunningham/';
import { FooterType } from '@/features/footer';
import { PostHogConf } from '@/services';

interface ThemeCustomization {
  footer?: FooterType;
  translations?: Resource;
}

export enum FeatureFlagState {
  ENABLED = 'enabled',
  DISABLED = 'disabled',
  DYNAMIC = 'dynamic',
}

interface FeatureFlags {
  [key: string]: FeatureFlagState;
}

// Custom feature flags for optional features
export interface FeatureFlagsCustom {
  [key: string]: boolean;
}

// Tool display names for human-readable tool labels
export interface ToolDisplayNames {
  [toolName: string]: string;
}

// Configurable prompt suggestion
export interface PromptSuggestion {
  icon: string;
  title: string;
  prompt: string;
}

export interface FeedbackUrls {
  form_url?: string | null;
  tchap_url?: string | null;
}

export interface ConfigResponse {
  ACTIVATION_REQUIRED: boolean;
  CRISP_WEBSITE_ID?: string;
  ENVIRONMENT: string;
  FEATURE_FLAGS: FeatureFlags;
  FRONTEND_CSS_URL?: string;
  FRONTEND_HOMEPAGE_FEATURE_ENABLED?: boolean;
  FRONTEND_THEME?: Theme;
  LANGUAGES: [string, string][];
  LANGUAGE_CODE: string;
  MEDIA_BASE_URL?: string;
  POSTHOG_KEY?: PostHogConf;
  SENTRY_DSN?: string;
  FILE_UPLOAD_MODE?: string;
  theme_customization?: ThemeCustomization;
  chat_upload_accept?: string;
  feature_flags_custom?: FeatureFlagsCustom;
  tool_display_names?: ToolDisplayNames;
  prompt_suggestions?: PromptSuggestion[];
  feedback_urls?: FeedbackUrls;
}

const LOCAL_STORAGE_KEY = 'conversations_config';

function getCachedTranslation() {
  try {
    const jsonString = localStorage.getItem(LOCAL_STORAGE_KEY);
    return jsonString ? (JSON.parse(jsonString) as ConfigResponse) : undefined;
  } catch {
    return undefined;
  }
}

function setCachedTranslation(translations: ConfigResponse) {
  localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(translations));
}

export const getConfig = async (): Promise<ConfigResponse> => {
  const response = await fetchAPI(`config/`);

  if (!response.ok) {
    throw new APIError('Failed to get the doc', await errorCauses(response));
  }

  const config = response.json() as Promise<ConfigResponse>;
  setCachedTranslation(await config);

  return config;
};

export const KEY_CONFIG = 'config';

export function useConfig() {
  const cachedData = getCachedTranslation();
  const oneHour = 1000 * 60 * 60;

  return useQuery<ConfigResponse, APIError, ConfigResponse>({
    queryKey: [KEY_CONFIG],
    queryFn: () => getConfig(),
    initialData: cachedData,
    staleTime: oneHour,
    initialDataUpdatedAt: Date.now() - oneHour, // Force initial data to be considered stale
  });
}
