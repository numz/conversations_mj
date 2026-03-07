import { render, screen, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { FeedbackButtons } from '../FeedbackButtons';

const mockScoreMessage = jest.fn();
jest.mock('@/features/chat/api/useScoreMessage', () => ({
  scoreMessage: (...args) => mockScoreMessage(...args),
}));

const mockShowToast = jest.fn();
jest.mock('@/components', () => ({
  Box: ({ children, as: Tag = 'div', ...props }) => {
    const Element = Tag;
    return <Element {...props}>{children}</Element>;
  },
  Text: ({ children, ...props }) => <span {...props}>{children}</span>,
  useToast: () => ({ showToast: mockShowToast }),
}));

jest.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key) => key,
  }),
}));

jest.mock('@openfun/cunningham-react', () => ({
  Button: ({ children, onClick, icon, ...props }) => (
    <button onClick={onClick} {...props}>
      {icon}
      {children}
    </button>
  ),
  Modal: ({ children, isOpen, title, leftActions, rightActions }) =>
    isOpen ? (
      <div data-testid="feedback-modal">
        <div data-testid="modal-title">{title}</div>
        <div>{children}</div>
        <div data-testid="modal-left-actions">{leftActions}</div>
        <div data-testid="modal-right-actions">{rightActions}</div>
      </div>
    ) : null,
  ModalSize: { SMALL: 'small' },
  TextArea: ({ label, value, onChange, ...props }) => (
    <textarea
      aria-label={label}
      value={value}
      onChange={onChange}
      {...props}
    />
  ),
}));

describe('FeedbackButtons', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockScoreMessage.mockResolvedValue(undefined);
  });

  const defaultProps = {
    conversationId: 'conv-123',
    messageId: 'msg-456',
  };

  it('renders thumbs up and thumbs down buttons', () => {
    render(<FeedbackButtons {...defaultProps} />);
    expect(screen.getByLabelText('Feedback positif')).toBeTruthy();
    expect(screen.getByLabelText('Feedback Négatif')).toBeTruthy();
  });

  it('sends positive feedback on thumbs up click', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback positif'));
    });

    expect(mockScoreMessage).toHaveBeenCalledWith({
      conversationId: 'conv-123',
      message_id: 'msg-456',
      value: 'positive',
      comment: undefined,
      categories: undefined,
    });
  });

  it('sends negative feedback directly when localFeedbackEnabled is off', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={false} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback Négatif'));
    });

    expect(mockScoreMessage).toHaveBeenCalledWith({
      conversationId: 'conv-123',
      message_id: 'msg-456',
      value: 'negative',
      comment: undefined,
      categories: undefined,
    });
    expect(screen.queryByTestId('feedback-modal')).toBeNull();
  });

  it('opens modal on thumbs down when localFeedbackEnabled is on', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={true} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback Négatif'));
    });

    expect(screen.getByTestId('feedback-modal')).toBeTruthy();
    expect(mockScoreMessage).not.toHaveBeenCalled();
  });

  it('does not render modal when localFeedbackEnabled is off', () => {
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={false} />);
    expect(screen.queryByTestId('feedback-modal')).toBeNull();
  });

  it('displays feedback categories in modal', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={true} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback Négatif'));
    });

    expect(screen.getByText('Réponse incorrecte')).toBeTruthy();
    expect(screen.getByText('Réponse incomplète')).toBeTruthy();
    expect(screen.getByText('Hors sujet')).toBeTruthy();
    expect(screen.getByText('Mal formatée')).toBeTruthy();
    expect(screen.getByText('Trop longue')).toBeTruthy();
    expect(screen.getByText('Sources manquantes')).toBeTruthy();
  });

  it('submits negative feedback with comment and categories', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={true} />);

    // Open modal
    await act(async () => {
      await user.click(screen.getByLabelText('Feedback Négatif'));
    });

    // Select a category
    await act(async () => {
      await user.click(screen.getByText('Réponse incorrecte'));
    });

    // Type a comment
    const textarea = screen.getByLabelText('Votre commentaire (facultatif)');
    await act(async () => {
      await user.type(textarea, 'Wrong answer');
    });

    // Submit
    await act(async () => {
      await user.click(screen.getByLabelText('Envoyer le retour'));
    });

    expect(mockScoreMessage).toHaveBeenCalledWith({
      conversationId: 'conv-123',
      message_id: 'msg-456',
      value: 'negative',
      comment: 'Wrong answer',
      categories: ['incorrect'],
    });
  });

  it('calls onFeedbackUpdate callback on success', async () => {
    const onFeedbackUpdate = jest.fn();
    const user = userEvent.setup();
    render(
      <FeedbackButtons
        {...defaultProps}
        onFeedbackUpdate={onFeedbackUpdate}
      />,
    );

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback positif'));
    });

    expect(onFeedbackUpdate).toHaveBeenCalledWith('positive');
  });

  it('shows success toast on feedback submission', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} />);

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback positif'));
    });

    expect(mockShowToast).toHaveBeenCalledWith(
      'success',
      'Merci de votre retour',
    );
  });

  it('initializes with initialFeedback prop', () => {
    render(
      <FeedbackButtons {...defaultProps} initialFeedback="positive" />,
    );
    // The filled thumb up SVG should be rendered (we can't easily test SVG content,
    // but we verify no error is thrown and the component renders)
    expect(screen.getByLabelText('Feedback positif')).toBeTruthy();
  });

  it('does not send feedback when conversationId is undefined', async () => {
    const user = userEvent.setup();
    render(
      <FeedbackButtons
        conversationId={undefined}
        messageId="msg-456"
      />,
    );

    await act(async () => {
      await user.click(screen.getByLabelText('Feedback positif'));
    });

    expect(mockScoreMessage).not.toHaveBeenCalled();
  });

  it('closes modal on cancel button click', async () => {
    const user = userEvent.setup();
    render(<FeedbackButtons {...defaultProps} localFeedbackEnabled={true} />);

    // Open modal
    await act(async () => {
      await user.click(screen.getByLabelText('Feedback Négatif'));
    });
    expect(screen.getByTestId('feedback-modal')).toBeTruthy();

    // Click cancel
    await act(async () => {
      await user.click(screen.getByLabelText('Annuler'));
    });
    expect(screen.queryByTestId('feedback-modal')).toBeNull();
  });
});
