/* eslint-disable testing-library/no-unnecessary-act, @typescript-eslint/require-await */
import { act, renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';

import { useClipboard } from '../useClipboard';

// --- Mock marked ---
jest.mock('marked', () => ({
  marked: (text: string) => `<p>${text}</p>`,
}));

// --- Mock useToast ---
const mockShowToast = jest.fn();
jest.mock('@/components', () => ({
  useToast: () => ({ showToast: mockShowToast }),
}));

// --- Mock react-i18next ---
jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

// Polyfill ClipboardItem for jsdom
if (typeof globalThis.ClipboardItem === 'undefined') {
  globalThis.ClipboardItem = class ClipboardItem {
    readonly types: string[];
    private items: Record<string, Blob>;
    constructor(items: Record<string, Blob>) {
      this.items = items;
      this.types = Object.keys(items);
    }
    async getType(type: string): Promise<Blob> {
      return this.items[type];
    }
  } as unknown as typeof ClipboardItem;
}

const wrapper = ({ children }: { children: ReactNode }) => <>{children}</>;

// Helper to flush promise chains
const flushPromises = () =>
  act(async () => {
    await new Promise((r) => setTimeout(r, 50));
  });

describe('useClipboard', () => {
  let mockWriteText: jest.Mock;
  let mockWrite: jest.Mock;

  beforeEach(() => {
    jest.clearAllMocks();
    mockWriteText = jest.fn().mockResolvedValue(undefined);
    mockWrite = jest.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: mockWriteText,
        write: mockWrite,
      },
    });
  });

  describe('rich=false (default)', () => {
    it('copies plain text via writeText', async () => {
      const { result } = renderHook(() => useClipboard(), { wrapper });

      await act(async () => {
        result.current('hello world');
      });
      await flushPromises();

      expect(mockWriteText).toHaveBeenCalledWith('hello world');
      expect(mockWrite).not.toHaveBeenCalled();
    });

    it('shows success toast on copy', async () => {
      const { result } = renderHook(() => useClipboard(), { wrapper });

      await act(async () => {
        result.current('text');
      });
      await flushPromises();

      expect(mockShowToast).toHaveBeenCalledWith(
        'success',
        'Copied',
        'content_copy',
        3000,
      );
    });

    it('shows error toast on failure', async () => {
      mockWriteText.mockRejectedValue(new Error('fail'));
      const { result } = renderHook(() => useClipboard(), { wrapper });

      await act(async () => {
        result.current('text');
      });
      await flushPromises();

      expect(mockShowToast).toHaveBeenCalledWith(
        'error',
        'Failed to copy',
        'content_copy',
        3000,
      );
    });

    it('uses custom success/error messages', async () => {
      const { result } = renderHook(() => useClipboard(), { wrapper });

      await act(async () => {
        result.current('text', 'Custom success', 'Custom error');
      });
      await flushPromises();

      expect(mockShowToast).toHaveBeenCalledWith(
        'success',
        'Custom success',
        'content_copy',
        3000,
      );
    });
  });

  describe('rich=true', () => {
    it('calls clipboard.write with ClipboardItem', async () => {
      const { result } = renderHook(() => useClipboard(true), { wrapper });

      await act(async () => {
        result.current('**bold**');
      });
      await flushPromises();

      expect(mockWrite).toHaveBeenCalledTimes(1);
      expect(mockWriteText).not.toHaveBeenCalled();
    });

    it('shows success toast on rich copy', async () => {
      const { result } = renderHook(() => useClipboard(true), { wrapper });

      await act(async () => {
        result.current('text');
      });
      await flushPromises();

      expect(mockShowToast).toHaveBeenCalledWith(
        'success',
        'Copied',
        'content_copy',
        3000,
      );
    });

    it('falls back to writeText when write() fails', async () => {
      mockWrite.mockRejectedValue(new Error('not supported'));
      const { result } = renderHook(() => useClipboard(true), { wrapper });

      await act(async () => {
        result.current('markdown text');
      });
      await flushPromises();

      expect(mockWrite).toHaveBeenCalled();
      expect(mockWriteText).toHaveBeenCalledWith('markdown text');
      expect(mockShowToast).toHaveBeenCalledWith(
        'success',
        'Copied',
        'content_copy',
        3000,
      );
    });

    it('shows error when both write() and writeText() fail', async () => {
      mockWrite.mockRejectedValue(new Error('not supported'));
      mockWriteText.mockRejectedValue(new Error('also fails'));
      const { result } = renderHook(() => useClipboard(true), { wrapper });

      await act(async () => {
        result.current('text');
      });
      await flushPromises();

      expect(mockShowToast).toHaveBeenCalledWith(
        'error',
        'Failed to copy',
        'content_copy',
        3000,
      );
    });
  });

  describe('rich parameter toggling', () => {
    it('returns different callbacks for rich=true vs rich=false', () => {
      const { result: resultPlain } = renderHook(() => useClipboard(false), {
        wrapper,
      });
      const { result: resultRich } = renderHook(() => useClipboard(true), {
        wrapper,
      });

      expect(resultPlain.current).not.toBe(resultRich.current);
    });
  });
});
