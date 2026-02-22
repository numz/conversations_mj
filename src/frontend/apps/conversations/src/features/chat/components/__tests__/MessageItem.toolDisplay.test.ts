/**
 * Tests for tool display name resolution logic — Feature 8: Tool Display Names.
 *
 * The logic in MessageItem resolves a tool invocation name to a user-friendly
 * display label using:
 *   toolDisplayNames[toolName] || toolDisplayNames['_default'] || t('Search...')
 */

describe('Tool display name resolution', () => {
  const t = (key: string) => key;

  function resolveToolLabel(
    toolName: string,
    toolDisplayNames: Record<string, string>,
  ): string {
    return (
      toolDisplayNames[toolName] ||
      toolDisplayNames['_default'] ||
      t('Search...')
    );
  }

  it('returns exact match when tool name exists in map', () => {
    const map = { web_search: 'Searching the web', calculator: 'Calculating' };
    expect(resolveToolLabel('web_search', map)).toBe('Searching the web');
  });

  it('falls back to _default when tool name not in map', () => {
    const map = { _default: 'Using tool...' };
    expect(resolveToolLabel('unknown_tool', map)).toBe('Using tool...');
  });

  it('falls back to t("Search...") when neither match nor _default', () => {
    expect(resolveToolLabel('unknown_tool', {})).toBe('Search...');
  });

  it('prefers exact match over _default', () => {
    const map = {
      legifrance_search: 'Searching Légifrance',
      _default: 'Processing...',
    };
    expect(resolveToolLabel('legifrance_search', map)).toBe('Searching Légifrance');
  });

  it('handles empty tool name', () => {
    const map = { _default: 'Working...' };
    expect(resolveToolLabel('', map)).toBe('Working...');
  });
});
