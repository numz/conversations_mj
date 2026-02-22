import { marked } from 'marked';
import { useCallback } from 'react';
import { useTranslation } from 'react-i18next';

import { useToast } from '@/components';

export const useClipboard = (rich = false) => {
  const { showToast } = useToast();
  const { t } = useTranslation();

  return useCallback(
    (text: string, successMessage?: string, errorMessage?: string) => {
      const onSuccess = () => {
        showToast(
          'success',
          successMessage ?? t('Copied'),
          'content_copy',
          3000,
        );
      };
      const onError = () => {
        showToast(
          'error',
          errorMessage ?? t('Failed to copy'),
          'content_copy',
          3000,
        );
      };

      if (rich) {
        // Convert Markdown to HTML for rich text editors (Word, Google Docs, etc.)
        void Promise.resolve(marked(text)).then((html) => {
          // Try to write both HTML and plain text formats
          // Rich text editors will use HTML, plain text editors will use the plain text
          navigator.clipboard
            .write([
              new ClipboardItem({
                'text/html': new Blob([html], { type: 'text/html' }),
                'text/plain': new Blob([text], { type: 'text/plain' }),
              }),
            ])
            .then(onSuccess)
            // Fallback for browsers that don't support ClipboardItem (e.g., Firefox)
            .catch(() =>
              navigator.clipboard
                .writeText(text)
                .then(onSuccess)
                .catch(onError),
            );
        });
      } else {
        navigator.clipboard.writeText(text).then(onSuccess).catch(onError);
      }
    },
    [t, showToast, rich],
  );
};
