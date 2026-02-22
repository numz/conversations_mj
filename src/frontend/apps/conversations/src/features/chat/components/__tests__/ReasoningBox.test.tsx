import { render, screen, fireEvent, act } from '@testing-library/react';
import type { ReactNode } from 'react';

import { ReasoningBox } from '../ReasoningBox';

// Mock dependencies
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

const mockFeatureFlags: Record<string, boolean> = {};
jest.mock('@/core/config/api', () => ({
  useFeatureFlags: () => mockFeatureFlags,
}));

jest.mock('@/components', () => ({
  Box: ({ children, onClick, onKeyDown, role, tabIndex, className, id, ...rest }: {
    children?: ReactNode;
    onClick?: () => void;
    onKeyDown?: (e: { key: string; preventDefault: () => void }) => void;
    role?: string;
    tabIndex?: number;
    className?: string;
    id?: string;
    [key: string]: unknown;
  }) => (
    <div
      onClick={onClick}
      onKeyDown={onKeyDown as unknown as React.KeyboardEventHandler}
      role={role}
      tabIndex={tabIndex}
      className={className}
      id={id}
      data-testid={className}
    >
      {children}
    </div>
  ),
  Icon: ({ iconName }: { iconName: string }) => <span data-testid={`icon-${iconName}`} />,
  Text: ({ children }: { children?: ReactNode }) => <span>{children}</span>,
}));

jest.mock('@/components/Loader', () => ({
  Loader: () => <span data-testid="loader" />,
}));

describe('ReasoningBox', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    // Reset feature flags
    Object.keys(mockFeatureFlags).forEach((k) => delete mockFeatureFlags[k]);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders nothing when no reasoning and no processingLabel', () => {
    const { container } = render(
      <ReasoningBox reasoning="" isStreaming={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders nothing when feature flag is disabled', () => {
    mockFeatureFlags.reasoning_box_enabled = false;
    const { container } = render(
      <ReasoningBox reasoning="some reasoning" isStreaming={false} />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders when feature flag is not explicitly set (defaults to showing)', () => {
    render(
      <ReasoningBox reasoning="thinking out loud" isStreaming={false} />,
    );
    expect(screen.getByText('Reasoning')).toBeInTheDocument();
  });

  it('renders reasoning text', () => {
    render(
      <ReasoningBox reasoning="Step 1: analyze" isStreaming={false} />,
    );
    expect(screen.getAllByText('Step 1: analyze').length).toBeGreaterThanOrEqual(1);
  });

  it('shows processing label with loader when provided', () => {
    render(
      <ReasoningBox reasoning="" isStreaming={true} processingLabel="Searching..." />,
    );
    expect(screen.getByText('Searching...')).toBeInTheDocument();
    expect(screen.getByTestId('loader')).toBeInTheDocument();
  });

  it('shows streaming indicator when streaming', () => {
    render(
      <ReasoningBox reasoning="thinking" isStreaming={true} />,
    );
    expect(screen.getByTestId('reasoning-streaming-indicator')).toBeInTheDocument();
  });

  it('does not show streaming indicator when not streaming', () => {
    render(
      <ReasoningBox reasoning="done thinking" isStreaming={false} />,
    );
    expect(screen.queryByTestId('reasoning-streaming-indicator')).not.toBeInTheDocument();
  });

  it('truncates last line preview to 100 chars', () => {
    const longLine = 'A'.repeat(150);
    render(
      <ReasoningBox reasoning={longLine} isStreaming={false} />,
    );
    // Should show truncated version with "..."
    expect(screen.getByText('A'.repeat(100) + '...')).toBeInTheDocument();
  });

  it('expands on click', () => {
    render(
      <ReasoningBox reasoning="content here" isStreaming={false} />,
    );

    const header = screen.getByTestId('reasoning-header');
    fireEvent.click(header);

    // After click, the expand_less icon should appear
    expect(screen.getByTestId('icon-expand_less')).toBeInTheDocument();
  });

  it('collapses back on second click', () => {
    render(
      <ReasoningBox reasoning="content here" isStreaming={false} />,
    );

    const header = screen.getByTestId('reasoning-header');
    fireEvent.click(header); // expand
    fireEvent.click(header); // collapse

    expect(screen.getByTestId('icon-expand_more')).toBeInTheDocument();
  });
});
