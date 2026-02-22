import { useEffect, useRef, useState } from 'react';

/**
 * Hook that creates a typewriter effect for text.
 * Only animates when the text changes for the same key (e.g., conversation ID).
 * When the key changes, it shows the full text immediately.
 *
 * @param text - The final text to display
 * @param key - A unique key (e.g., conversation ID) to track changes
 * @param speed - Milliseconds per character (default: 25ms)
 * @returns The text to display (animated or final)
 */
export const useTypewriter = (
  text: string,
  key: string,
  speed: number = 25,
): string => {
  const [displayedText, setDisplayedText] = useState(text);
  const previousTextRef = useRef(text);
  const previousKeyRef = useRef(key);
  const animationRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // Clear any existing animation
    if (animationRef.current) {
      clearInterval(animationRef.current);
      animationRef.current = null;
    }

    // If key changed (different conversation), show full text immediately
    if (previousKeyRef.current !== key) {
      previousKeyRef.current = key;
      previousTextRef.current = text;
      setDisplayedText(text);
      return;
    }

    // If text hasn't changed, do nothing
    if (previousTextRef.current === text) {
      return;
    }

    // Text changed for same key - start typewriter animation
    previousTextRef.current = text;

    // Start from empty and type out
    let currentIndex = 0;
    setDisplayedText('');

    animationRef.current = setInterval(() => {
      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1));
        currentIndex++;
      } else {
        if (animationRef.current) {
          clearInterval(animationRef.current);
          animationRef.current = null;
        }
      }
    }, speed);

    return () => {
      if (animationRef.current) {
        clearInterval(animationRef.current);
        animationRef.current = null;
      }
    };
  }, [text, key, speed]);

  return displayedText;
};
