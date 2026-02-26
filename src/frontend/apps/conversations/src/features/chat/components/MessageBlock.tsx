// Memoized components for a single completed markdown blocks - only re-renders when content changes
import rehypeShikiFromHighlighter from '@shikijs/rehype/core';
import React, { use } from 'react';
import { Components, MarkdownHooks } from 'react-markdown';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';

import { Text } from '@/components';
import { CodeBlock } from '@/features/chat/components/CodeBlock';
import { TableWithExport } from '@/features/chat/components/TableWithExport';

// Memoized markdown plugins - created once at module level
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const REMARK_PLUGINS: any[] = [remarkGfm, remarkMath];
// // eslint-disable-next-line @typescript-eslint/no-explicit-any

import { getHighlighter } from '../utils/shiki';

const highlighterPromise = getHighlighter();

// Order matters: rehypeRaw parses HTML in markdown (e.g. <br>),
// rehypeSanitize strips dangerous HTML, then KaTeX and Shiki
// run after sanitization so their output is preserved.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const rehypePluginsPromise: Promise<any[]> = highlighterPromise.then(
  (highlighter) => [
    rehypeRaw,
    rehypeSanitize,
    rehypeKatex,
    [
      rehypeShikiFromHighlighter,
      highlighter,
      {
        theme: 'github-dark-dimmed',
        fallbackLanguage: 'plaintext',
      },
    ],
  ],
);

// Memoized markdown components - created once at module level
const MARKDOWN_COMPONENTS: Components = {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  p: ({ node, ...props }) => (
    <Text
      as="p"
      $css="display: block"
      $theme="greyscale"
      $variation="850"
      {...props}
    />
  ),
  a: ({ children, ...props }) => (
    <a target="_blank" {...props}>
      {children}
    </a>
  ),

  pre: ({
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    node,
    children,
    ...props
  }) => <CodeBlock {...props}>{children}</CodeBlock>,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  table: ({ node, children, ...props }) => (
    <TableWithExport {...props}>{children}</TableWithExport>
  ),
};

export const CompletedMarkdownBlock = React.memo(
  ({ content }: { content: string }) => {
    const rehypePlugins = use(rehypePluginsPromise);
    return (
      <MarkdownHooks
        remarkPlugins={REMARK_PLUGINS}
        rehypePlugins={rehypePlugins}
        components={MARKDOWN_COMPONENTS}
      >
        {content}
      </MarkdownHooks>
    );
  },
  (prev, next) => prev.content === next.content,
);

CompletedMarkdownBlock.displayName = 'CompletedMarkdownBlock';

export const RawTextBlock = ({ content }: { content: string }) => (
  <Text
    as="div"
    $css="white-space: pre-wrap; display: block;"
    $theme="greyscale"
    $variation="850"
  >
    {content}
  </Text>
);
