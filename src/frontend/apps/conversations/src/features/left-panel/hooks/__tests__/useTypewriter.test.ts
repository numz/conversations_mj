import { renderHook, act } from '@testing-library/react';

import { useTypewriter } from '../useTypewriter';

describe('useTypewriter', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('returns initial text immediately on first render', () => {
    const { result } = renderHook(() => useTypewriter('Hello', 'key1'));
    expect(result.current).toBe('Hello');
  });

  it('shows full text immediately when key changes', () => {
    const { result, rerender } = renderHook(
      ({ text, key }) => useTypewriter(text, key),
      { initialProps: { text: 'First', key: 'key1' } },
    );

    expect(result.current).toBe('First');

    // Change key (simulate switching conversation)
    rerender({ text: 'Second title', key: 'key2' });
    expect(result.current).toBe('Second title');
  });

  it('animates text when text changes for same key', () => {
    const { result, rerender } = renderHook(
      ({ text, key }) => useTypewriter(text, key, 25),
      { initialProps: { text: 'Old', key: 'key1' } },
    );

    expect(result.current).toBe('Old');

    // Change text, same key
    rerender({ text: 'New title', key: 'key1' });

    // Should start animation from empty
    expect(result.current).toBe('');

    // Advance timers to type characters
    act(() => {
      jest.advanceTimersByTime(25);
    });
    expect(result.current).toBe('N');

    act(() => {
      jest.advanceTimersByTime(25);
    });
    expect(result.current).toBe('Ne');
  });

  it('completes animation after enough time', () => {
    const { result, rerender } = renderHook(
      ({ text, key }) => useTypewriter(text, key, 25),
      { initialProps: { text: 'A', key: 'k1' } },
    );

    rerender({ text: 'AB', key: 'k1' });

    // Advance enough for both characters
    act(() => {
      jest.advanceTimersByTime(25 * 3);
    });

    expect(result.current).toBe('AB');
  });

  it('does not animate when text stays the same', () => {
    const { result, rerender } = renderHook(
      ({ text, key }) => useTypewriter(text, key),
      { initialProps: { text: 'Same', key: 'k1' } },
    );

    rerender({ text: 'Same', key: 'k1' });
    expect(result.current).toBe('Same');
  });

  it('cleans up interval on unmount', () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    const { result, rerender, unmount } = renderHook(
      ({ text, key }) => useTypewriter(text, key, 25),
      { initialProps: { text: 'A', key: 'k1' } },
    );

    // Trigger animation
    rerender({ text: 'New text', key: 'k1' });

    unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});
