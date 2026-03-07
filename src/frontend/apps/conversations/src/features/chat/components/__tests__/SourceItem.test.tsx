import { CunninghamProvider } from '@openfun/cunningham-react';
import { render, screen } from '@testing-library/react';

import { SourceItem } from '../SourceItem';

// Mock next/navigation (used by StyledLink)
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

describe('SourceItem', () => {
  describe('extractTitleFromUrl fallback', () => {
    it('displays backend title when provided', () => {
      renderWithProviders(
        <SourceItem
          url="https://www.legifrance.gouv.fr/codes/article/123"
          title="Article 1240 du Code civil [Modifie]"
        />,
      );
      expect(
        screen.getByText('Article 1240 du Code civil [Modifie]'),
      ).toBeInTheDocument();
    });

    it('extracts "Legifrance" from legifrance.gouv.fr URL when no title', () => {
      renderWithProviders(
        <SourceItem url="https://www.legifrance.gouv.fr/codes/article/123" />,
      );
      expect(screen.getByText('Légifrance')).toBeInTheDocument();
    });

    it('extracts "Cour de cassation" from courdecassation.fr URL', () => {
      renderWithProviders(
        <SourceItem url="https://www.courdecassation.fr/decision/12345" />,
      );
      expect(screen.getByText('Cour de cassation')).toBeInTheDocument();
    });

    it('extracts Wikipedia article title from URL', () => {
      renderWithProviders(
        <SourceItem url="https://fr.wikipedia.org/wiki/Code_civil_(France)" />,
      );
      expect(screen.getByText('Code civil (France)')).toBeInTheDocument();
    });

    it('falls back to hostname for unknown domains', () => {
      renderWithProviders(<SourceItem url="https://example.com/" />);
      expect(screen.getByText('example.com')).toBeInTheDocument();
    });

    it('uses last path segment for generic URLs', () => {
      renderWithProviders(
        <SourceItem url="https://example.com/some-document-title" />,
      );
      expect(
        screen.getByText('some document title'),
      ).toBeInTheDocument();
    });

    it('prefers backend title over extracted title', () => {
      renderWithProviders(
        <SourceItem
          url="https://www.legifrance.gouv.fr/codes/article/123"
          title="Code civil"
        />,
      );
      expect(screen.getByText('Code civil')).toBeInTheDocument();
      expect(screen.queryByText('Légifrance')).not.toBeInTheDocument();
    });

    it('treats null title as absent', () => {
      renderWithProviders(
        <SourceItem
          url="https://www.legifrance.gouv.fr/codes/article/123"
          title={null}
        />,
      );
      expect(screen.getByText('Légifrance')).toBeInTheDocument();
    });
  });

  describe('rendering', () => {
    it('renders as a link for http URLs', () => {
      renderWithProviders(
        <SourceItem url="https://example.com/page" title="Example" />,
      );
      const link = screen.getByRole('link');
      expect(link).toHaveAttribute('href', 'https://example.com/page');
      expect(link).toHaveAttribute('target', '_blank');
    });

    it('renders as plain text for non-http URLs', () => {
      renderWithProviders(<SourceItem url="file:///local/path" />);
      expect(screen.queryByRole('link')).not.toBeInTheDocument();
      expect(screen.getByText('file:///local/path')).toBeInTheDocument();
    });
  });
});
