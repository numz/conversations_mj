import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { css } from 'styled-components';

import { Box, useToast } from '@/components';
import { useCunninghamTheme } from '@/cunningham';
import { useUpdateConversation } from '@/features/chat/api/useUpdateConversation';
import { ChatConversation } from '@/features/chat/types';

import BubbleIcon from '../assets/bubble-bold.svg';

const MAX_TITLE_LENGTH = 100;
const MIN_TITLE_LENGTH = 1;

interface EditableConversationTitleProps {
  conversation: ChatConversation;
  onClose: () => void;
}

export const EditableConversationTitle = ({
  conversation,
  onClose,
}: EditableConversationTitleProps) => {
  const { t } = useTranslation();
  const { spacingsTokens, colorsTokens } = useCunninghamTheme();
  const { showToast } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);
  const isReadyRef = useRef(false);
  const [title, setTitle] = useState(conversation.title || '');
  const [error, setError] = useState<string | null>(null);

  const { mutate: updateConversation, isPending } = useUpdateConversation({
    onSuccess: () => {
      showToast('success', t('Conversation renamed'));
      onClose();
    },
    onError: () => {
      showToast('error', t('Failed to rename conversation'));
    },
  });

  useEffect(() => {
    // Focus and select all text when entering edit mode
    // Use a delay to avoid conflicts with dropdown closing
    const focusTimer = setTimeout(() => {
      if (inputRef.current) {
        inputRef.current.focus();
        inputRef.current.select();
      }
    }, 50);

    // Only enable blur handling after component is stable
    const readyTimer = setTimeout(() => {
      isReadyRef.current = true;
    }, 200);

    return () => {
      clearTimeout(focusTimer);
      clearTimeout(readyTimer);
    };
  }, []);

  const validateTitle = (value: string): string | null => {
    const trimmed = value.trim();
    if (trimmed.length < MIN_TITLE_LENGTH) {
      return t('Title cannot be empty');
    }
    if (trimmed.length > MAX_TITLE_LENGTH) {
      return t('Title is too long (max {{max}} characters)', {
        max: MAX_TITLE_LENGTH,
      });
    }
    return null;
  };

  const handleSubmit = () => {
    const trimmedTitle = title.trim();
    const validationError = validateTitle(trimmedTitle);

    if (validationError) {
      setError(validationError);
      showToast('error', validationError);
      setTitle(conversation.title || '');
      onClose();
      return;
    }

    if (trimmedTitle !== conversation.title) {
      updateConversation({
        conversationId: conversation.id,
        title: trimmedTitle,
      });
    } else {
      onClose();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (value.length <= MAX_TITLE_LENGTH) {
      setTitle(value);
      setError(null);
    }
  };

  const handleBlur = () => {
    // Ignore blur events until component is ready (avoids conflicts with dropdown closing)
    if (!isReadyRef.current) {
      return;
    }

    // Small delay to allow click events to fire first
    setTimeout(() => {
      if (!isPending) {
        handleSubmit();
      }
    }, 100);
  };

  return (
    <Box
      $direction="row"
      $gap={spacingsTokens.sm}
      $overflow="auto"
      $align="center"
      $css="flex: 1; min-width: 0;"
    >
      <Box
        $direction="row"
        $align="center"
        $css={css`
          background-color: transparent;
          filter: drop-shadow(0px 2px 2px rgba(0, 0, 0, 0.05));
          flex-shrink: 0;
        `}
        $padding={`${spacingsTokens['3xs']} 0`}
      >
        <BubbleIcon
          aria-label={t('Simple chat icon')}
          color={colorsTokens['primary-500']}
        />
      </Box>
      <input
        ref={inputRef}
        type="text"
        value={title}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={handleBlur}
        disabled={isPending}
        maxLength={MAX_TITLE_LENGTH}
        aria-label={t('Conversation title')}
        aria-invalid={!!error}
        style={{
          flex: 1,
          minWidth: 0,
          padding: '4px 8px',
          fontSize: '14px',
          border: `1px solid ${error ? 'var(--c--theme--colors--danger-500)' : 'var(--c--theme--colors--primary-500)'}`,
          borderRadius: '4px',
          outline: 'none',
          backgroundColor: 'white',
        }}
      />
    </Box>
  );
};
