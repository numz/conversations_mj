/* eslint-disable @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-return, testing-library/no-unnecessary-act, @typescript-eslint/require-await */
import { CunninghamProvider } from '@openfun/cunningham-react';
import { act, render, waitFor } from '@testing-library/react';

import { Chat } from '../Chat';

// --- Mock ESM modules used by MessageBlock (transitive) ---
jest.mock('react-markdown', () => ({
  MarkdownHooks: ({ children }: { children: string }) => <div>{children}</div>,
}));
jest.mock('@shikijs/rehype/core', () => () => {});
jest.mock('../../utils/shiki', () => ({
  getHighlighter: () => Promise.resolve({}),
}));
jest.mock('rehype-katex', () => () => {});
jest.mock('rehype-raw', () => () => {});
jest.mock('rehype-sanitize', () => () => {});
jest.mock('remark-gfm', () => () => {});
jest.mock('remark-math', () => () => {});

// --- Mock katex CSS import ---
jest.mock('katex/dist/katex.min.css', () => ({}));

// --- Mock feature flags ---
let mockFeatureFlags: Record<string, boolean> = {};
jest.mock('@/core/config', () => ({
  useFeatureFlags: () => mockFeatureFlags,
}));

// --- Mock router (stable reference to avoid re-triggering useEffect) ---
const mockReplace = jest.fn();
const mockPush = jest.fn();
const stableRouter = {
  replace: mockReplace,
  push: mockPush,
  query: {},
  pathname: '/chat',
};
jest.mock('next/router', () => ({
  useRouter: () => stableRouter,
}));

// --- Mock getConversation to reject ---
const mockGetConversation = jest.fn();
jest.mock('@/features/chat/api/useConversation', () => ({
  getConversation: (...args: unknown[]) => mockGetConversation(...args),
}));

// --- Mock useChat ---
jest.mock('@/features/chat/api/useChat', () => ({
  useChat: () => ({
    messages: [],
    input: '',
    handleSubmit: jest.fn(),
    handleInputChange: jest.fn(),
    status: 'ready',
    stop: jest.fn(),
    setMessages: jest.fn(),
  }),
}));

// --- Mock useLLMConfiguration ---
jest.mock('@/features/chat/api/useLLMConfiguration', () => ({
  useLLMConfiguration: () => ({
    data: { models: [{ hrid: 'test', is_default: true, is_active: true }] },
  }),
  LLMModel: {},
}));

// --- Mock useCreateConversation ---
jest.mock('@/features/chat/api/useCreateConversation', () => ({
  useCreateChatConversation: () => ({
    mutate: jest.fn(),
  }),
}));

// --- Mock useUploadFile ---
jest.mock('@/features/attachments/hooks/useUploadFile', () => ({
  useUploadFile: () => ({
    uploadFile: jest.fn(),
    isErrorAttachment: false,
    errorAttachment: null,
  }),
}));

// --- Mock useClipboard ---
jest.mock('@/hook', () => ({
  useClipboard: () => jest.fn(),
}));

// --- Mock useResponsiveStore ---
jest.mock('@/stores', () => ({
  useResponsiveStore: () => ({ isMobile: false }),
}));

// --- Mock stores ---
jest.mock('../../stores/useChatPreferencesStore', () => ({
  useChatPreferencesStore: () => ({
    forceWebSearch: false,
    toggleForceWebSearch: jest.fn(),
    selectedModelHrid: null,
    setSelectedModelHrid: jest.fn(),
  }),
}));

jest.mock('../../stores/usePendingChatStore', () => ({
  usePendingChatStore: () => ({
    input: null,
    files: null,
    setPendingChat: jest.fn(),
    clearPendingChat: jest.fn(),
  }),
}));

jest.mock('../../stores/useScrollStore', () => ({
  useScrollStore: () => ({
    setIsAtTop: jest.fn(),
  }),
}));

// --- Mock hooks ---
jest.mock('../../hooks', () => ({
  useSourceMetadataCache: () => ({
    prefetchMetadata: jest.fn(),
    getMetadata: jest.fn(),
  }),
}));

// --- Mock child components that need ToastProvider ---
jest.mock('../InputChat', () => ({
  InputChat: () => <div data-testid="input-chat" />,
}));
jest.mock('../ChatError', () => ({
  ChatError: () => <div data-testid="chat-error" />,
}));
jest.mock('../MessageItem', () => ({
  MessageItem: () => <div data-testid="message-item" />,
}));

// --- Mock API ---
jest.mock('@/api', () => ({
  APIError: class extends Error {},
  errorCauses: jest.fn().mockResolvedValue('error'),
  fetchAPI: jest.fn(),
}));

// --- Mock i18next ---
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('Chat - conversation error redirect', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
      cb(0);
      return 0;
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('redirects to /chat when flag is enabled and fetch fails', async () => {
    mockFeatureFlags = { conversation_error_redirect_enabled: true };
    mockGetConversation.mockRejectedValue(new Error('Not found'));

    await act(async () => {
      render(
        <CunninghamProvider>
          <Chat initialConversationId="non-existent-id" />
        </CunninghamProvider>,
      );
    });

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/chat');
    });
  });

  it('does not redirect when flag is disabled and fetch fails', async () => {
    mockFeatureFlags = { conversation_error_redirect_enabled: false };
    mockGetConversation.mockRejectedValue(new Error('Not found'));

    await act(async () => {
      render(
        <CunninghamProvider>
          <Chat initialConversationId="non-existent-id" />
        </CunninghamProvider>,
      );
    });

    // Wait for the rejected promise to be handled
    await waitFor(() => {
      expect(mockGetConversation).toHaveBeenCalled();
    });

    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('does not redirect when flag is missing and fetch fails', async () => {
    mockFeatureFlags = {};
    mockGetConversation.mockRejectedValue(new Error('Not found'));

    await act(async () => {
      render(
        <CunninghamProvider>
          <Chat initialConversationId="non-existent-id" />
        </CunninghamProvider>,
      );
    });

    await waitFor(() => {
      expect(mockGetConversation).toHaveBeenCalled();
    });

    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('does not redirect when fetch succeeds', async () => {
    mockFeatureFlags = { conversation_error_redirect_enabled: true };
    mockGetConversation.mockResolvedValue({
      id: 'test-id',
      messages: [],
    });

    await act(async () => {
      render(
        <CunninghamProvider>
          <Chat initialConversationId="test-id" />
        </CunninghamProvider>,
      );
    });

    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });

    expect(mockReplace).not.toHaveBeenCalled();
  });

  it('does not fetch when no initialConversationId', async () => {
    mockFeatureFlags = { conversation_error_redirect_enabled: true };

    await act(async () => {
      render(
        <CunninghamProvider>
          <Chat initialConversationId={undefined} />
        </CunninghamProvider>,
      );
    });

    expect(mockGetConversation).not.toHaveBeenCalled();
    expect(mockReplace).not.toHaveBeenCalled();
  });
});
