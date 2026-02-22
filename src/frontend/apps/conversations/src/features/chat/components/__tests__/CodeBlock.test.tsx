import { CunninghamProvider } from '@openfun/cunningham-react';
import { fireEvent, render, screen } from '@testing-library/react';

import { CodeBlock } from '../CodeBlock';

// Mock useClipboard
const mockCopyToClipboard = jest.fn();
jest.mock('@/hook', () => ({
  useClipboard: () => mockCopyToClipboard,
}));

// Mock exportTextToTXT
const mockExportTextToTXT = jest.fn();
jest.mock('../../utils/exportText', () => ({
  exportTextToTXT: (...args: unknown[]) => mockExportTextToTXT(...args),
}));

// Mock useFeatureFlags
let mockFeatureFlags: Record<string, boolean> = {};
jest.mock('@/core/config', () => ({
  useFeatureFlags: () => mockFeatureFlags,
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const renderWithProviders = (ui: React.ReactNode) => {
  return render(<CunninghamProvider>{ui}</CunninghamProvider>);
};

describe('CodeBlock', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFeatureFlags = {};
  });

  it('renders children inside a pre element', () => {
    renderWithProviders(
      <CodeBlock>
        <code>console.log(test)</code>
      </CodeBlock>,
    );

    expect(screen.getByText('console.log(test)')).toBeInTheDocument();
  });

  it('always shows the Copy code button', () => {
    renderWithProviders(
      <CodeBlock>
        <code>test</code>
      </CodeBlock>,
    );

    expect(screen.getByText('Copy code')).toBeInTheDocument();
  });

  it('does not show Download button when flag is off', () => {
    mockFeatureFlags = { code_download_enabled: false };

    renderWithProviders(
      <CodeBlock>
        <code>test</code>
      </CodeBlock>,
    );

    expect(screen.queryByText('Download')).not.toBeInTheDocument();
  });

  it('does not show Download button when flag is missing', () => {
    mockFeatureFlags = {};

    renderWithProviders(
      <CodeBlock>
        <code>test</code>
      </CodeBlock>,
    );

    expect(screen.queryByText('Download')).not.toBeInTheDocument();
  });

  it('shows Download button when flag is on', () => {
    mockFeatureFlags = { code_download_enabled: true };

    renderWithProviders(
      <CodeBlock>
        <code>test</code>
      </CodeBlock>,
    );

    expect(screen.getByText('Download')).toBeInTheDocument();
  });

  it('calls copyToClipboard when Copy code is clicked', () => {
    renderWithProviders(
      <CodeBlock>
        <code>some code</code>
      </CodeBlock>,
    );

    fireEvent.click(screen.getByText('Copy code'));
    expect(mockCopyToClipboard).toHaveBeenCalled();
  });

  it('calls exportTextToTXT when Download is clicked', () => {
    mockFeatureFlags = { code_download_enabled: true };

    renderWithProviders(
      <CodeBlock>
        <code>downloadable code</code>
      </CodeBlock>,
    );

    fireEvent.click(screen.getByText('Download'));
    expect(mockExportTextToTXT).toHaveBeenCalledWith(
      'downloadable code',
      expect.stringMatching(/^code_\d{4}-\d{2}-\d{2}$/),
    );
  });

  it('generates download filename with current date', () => {
    mockFeatureFlags = { code_download_enabled: true };
    jest
      .spyOn(Date.prototype, 'toISOString')
      .mockReturnValue('2026-02-22T00:00:00.000Z');

    renderWithProviders(
      <CodeBlock>
        <code>test</code>
      </CodeBlock>,
    );

    fireEvent.click(screen.getByText('Download'));
    expect(mockExportTextToTXT).toHaveBeenCalledWith('test', 'code_2026-02-22');

    jest.restoreAllMocks();
  });
});
