import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { Feedback } from '../Feedback';

const DEFAULT_FORM_URL =
  'https://formulaire.beta.numerique.gouv.fr/r/assistant';
const DEFAULT_TCHAP_URL =
  'https://tchap.gouv.fr/#/room/!eAHyPLdVHMxNhKAbaC:agent.dinum.tchap.gouv.fr?via=agent.dinum.tchap.gouv.fr&via=agent.culture.tchap.gouv.fr&via=agent.education.tchap.gouv.fr';

const mockUseConfig = jest.fn();
jest.mock('@/core/config/api', () => ({
  useConfig: () => mockUseConfig(),
}));

// Mock cunningham Modal/Button to simplify rendering
let modalOpen = false;
jest.mock('@openfun/cunningham-react', () => ({
  Button: ({ children, onClick, ...props }: any) => (
    <button onClick={onClick} {...props}>
      {children}
    </button>
  ),
  Modal: ({ children, isOpen, ...props }: any) =>
    modalOpen ? <div data-testid="modal">{children}</div> : null,
  ModalSize: { MEDIUM: 'medium' },
  useModal: () => ({
    isOpen: modalOpen,
    open: () => {
      modalOpen = true;
    },
    close: () => {
      modalOpen = false;
    },
  }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.mock('@/components', () => ({
  Box: ({ children, as: Tag = 'div', $direction, $padding, $radius, $color, $gap, $css, $margin, ...props }: any) => {
    const Element = Tag;
    return <Element {...props}>{children}</Element>;
  },
  Text: ({ children, $size, $weight, $margin, ...props }: any) => (
    <span {...props}>{children}</span>
  ),
}));

describe('Feedback', () => {
  beforeEach(() => {
    modalOpen = false;
    mockUseConfig.mockReset();
  });

  it('renders the feedback button', () => {
    mockUseConfig.mockReturnValue({ data: undefined });
    render(<Feedback />);
    expect(screen.getByText('Give feedback')).toBeTruthy();
  });

  it('uses default URLs when config has no feedback_urls', async () => {
    mockUseConfig.mockReturnValue({ data: {} });
    modalOpen = true;
    render(<Feedback />);

    const links = screen.getAllByRole('link');
    const formLink = links.find(
      (l) => l.textContent?.includes('Give a quick opinion'),
    );
    const tchapLink = links.find(
      (l) => l.textContent?.includes('Write on Tchap'),
    );

    expect(formLink).toHaveAttribute('href', DEFAULT_FORM_URL);
    expect(tchapLink).toHaveAttribute('href', DEFAULT_TCHAP_URL);
  });

  it('uses default URLs when config is undefined', () => {
    mockUseConfig.mockReturnValue({ data: undefined });
    modalOpen = true;
    render(<Feedback />);

    const links = screen.getAllByRole('link');
    const formLink = links.find(
      (l) => l.textContent?.includes('Give a quick opinion'),
    );
    const tchapLink = links.find(
      (l) => l.textContent?.includes('Write on Tchap'),
    );

    expect(formLink).toHaveAttribute('href', DEFAULT_FORM_URL);
    expect(tchapLink).toHaveAttribute('href', DEFAULT_TCHAP_URL);
  });

  it('uses custom URLs from config when provided', () => {
    mockUseConfig.mockReturnValue({
      data: {
        feedback_urls: {
          form_url: 'https://custom-form.example.com',
          tchap_url: 'https://custom-tchap.example.com',
        },
      },
    });
    modalOpen = true;
    render(<Feedback />);

    const links = screen.getAllByRole('link');
    const formLink = links.find(
      (l) => l.textContent?.includes('Give a quick opinion'),
    );
    const tchapLink = links.find(
      (l) => l.textContent?.includes('Write on Tchap'),
    );

    expect(formLink).toHaveAttribute('href', 'https://custom-form.example.com');
    expect(tchapLink).toHaveAttribute(
      'href',
      'https://custom-tchap.example.com',
    );
  });

  it('falls back to defaults when config feedback_urls has empty strings', () => {
    mockUseConfig.mockReturnValue({
      data: {
        feedback_urls: {
          form_url: '',
          tchap_url: '',
        },
      },
    });
    modalOpen = true;
    render(<Feedback />);

    const links = screen.getAllByRole('link');
    const formLink = links.find(
      (l) => l.textContent?.includes('Give a quick opinion'),
    );
    const tchapLink = links.find(
      (l) => l.textContent?.includes('Write on Tchap'),
    );

    expect(formLink).toHaveAttribute('href', DEFAULT_FORM_URL);
    expect(tchapLink).toHaveAttribute('href', DEFAULT_TCHAP_URL);
  });
});
