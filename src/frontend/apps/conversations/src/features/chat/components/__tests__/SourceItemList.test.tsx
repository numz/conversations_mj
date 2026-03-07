import { CunninghamProvider } from '@openfun/cunningham-react';
import { render, screen } from '@testing-library/react';

import { SourceItemList } from '../SourceItemList';

// Mock next/navigation (used by StyledLink via SourceItem)
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    back: jest.fn(),
  }),
}));

const renderWithProviders = (ui: React.ReactNode) => {
  return render(<CunninghamProvider>{ui}</CunninghamProvider>);
};

const makeSourcePart = (url: string, title?: string) => ({
  type: 'source' as const,
  source: {
    sourceType: 'url' as const,
    id: `id-${url}`,
    url,
    title: title ?? undefined,
    providerMetadata: {},
  },
});

describe('SourceItemList', () => {
  it('renders nothing when parts is empty', () => {
    const { container } = renderWithProviders(<SourceItemList parts={[]} />);
    // CunninghamProvider wraps content; check that no source links are rendered
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('renders all unique sources', () => {
    const parts = [
      makeSourcePart('https://example.com/a', 'Source A'),
      makeSourcePart('https://example.com/b', 'Source B'),
    ];
    renderWithProviders(<SourceItemList parts={parts} />);
    expect(screen.getByText('Source A')).toBeInTheDocument();
    expect(screen.getByText('Source B')).toBeInTheDocument();
  });

  it('deduplicates sources by URL', () => {
    const parts = [
      makeSourcePart('https://example.com/a', 'Source A'),
      makeSourcePart('https://example.com/a', 'Source A duplicate'),
      makeSourcePart('https://example.com/b', 'Source B'),
    ];
    renderWithProviders(<SourceItemList parts={parts} />);
    expect(screen.getByText('Source A')).toBeInTheDocument();
    expect(screen.getByText('Source B')).toBeInTheDocument();
    expect(
      screen.queryByText('Source A duplicate'),
    ).not.toBeInTheDocument();
  });

  it('passes title from source to SourceItem', () => {
    const parts = [
      makeSourcePart(
        'https://www.legifrance.gouv.fr/codes/article/123',
        'Article 1240 du Code civil',
      ),
    ];
    renderWithProviders(<SourceItemList parts={parts} />);
    expect(
      screen.getByText('Article 1240 du Code civil'),
    ).toBeInTheDocument();
  });
});
