import {
  groupConversationsByDate,
  getTimeGroupLabel,
  formatRelativeTime,
} from '../groupConversationsByDate';

// Minimal ChatConversation mock
function makeConv(id: string, updatedAt: string) {
  return { id, updated_at: updatedAt } as Parameters<typeof groupConversationsByDate>[0][0];
}

describe('groupConversationsByDate', () => {
  it('groups conversations into today', () => {
    const now = new Date();
    const conv = makeConv('1', now.toISOString());
    const groups = groupConversationsByDate([conv]);

    expect(groups).toHaveLength(1);
    expect(groups[0].group).toBe('today');
    expect(groups[0].conversations).toHaveLength(1);
  });

  it('groups conversations into yesterday', () => {
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const conv = makeConv('1', yesterday.toISOString());
    const groups = groupConversationsByDate([conv]);

    expect(groups[0].group).toBe('yesterday');
  });

  it('groups conversations into last7days', () => {
    const threeDaysAgo = new Date();
    threeDaysAgo.setDate(threeDaysAgo.getDate() - 3);
    const conv = makeConv('1', threeDaysAgo.toISOString());
    const groups = groupConversationsByDate([conv]);

    expect(groups[0].group).toBe('last7days');
  });

  it('groups conversations into last30days', () => {
    const fifteenDaysAgo = new Date();
    fifteenDaysAgo.setDate(fifteenDaysAgo.getDate() - 15);
    const conv = makeConv('1', fifteenDaysAgo.toISOString());
    const groups = groupConversationsByDate([conv]);

    expect(groups[0].group).toBe('last30days');
  });

  it('groups conversations into older', () => {
    const sixtyDaysAgo = new Date();
    sixtyDaysAgo.setDate(sixtyDaysAgo.getDate() - 60);
    const conv = makeConv('1', sixtyDaysAgo.toISOString());
    const groups = groupConversationsByDate([conv]);

    expect(groups[0].group).toBe('older');
  });

  it('returns multiple groups in correct order', () => {
    const now = new Date();
    const yesterday = new Date();
    yesterday.setDate(yesterday.getDate() - 1);
    const old = new Date();
    old.setDate(old.getDate() - 60);

    const groups = groupConversationsByDate([
      makeConv('1', now.toISOString()),
      makeConv('2', yesterday.toISOString()),
      makeConv('3', old.toISOString()),
    ]);

    expect(groups.map((g) => g.group)).toEqual(['today', 'yesterday', 'older']);
  });

  it('skips empty groups', () => {
    const now = new Date();
    const groups = groupConversationsByDate([makeConv('1', now.toISOString())]);
    expect(groups).toHaveLength(1);
  });

  it('returns empty array for no conversations', () => {
    expect(groupConversationsByDate([])).toEqual([]);
  });
});

describe('getTimeGroupLabel', () => {
  it('returns correct labels for all groups', () => {
    expect(getTimeGroupLabel('today')).toBe('Today');
    expect(getTimeGroupLabel('yesterday')).toBe('Yesterday');
    expect(getTimeGroupLabel('last7days')).toBe('Last 7 days');
    expect(getTimeGroupLabel('last30days')).toBe('Last 30 days');
    expect(getTimeGroupLabel('older')).toBe('Older');
  });
});

describe('formatRelativeTime', () => {
  it('returns "just now" for recent timestamps (en)', () => {
    const now = new Date().toISOString();
    expect(formatRelativeTime(now, 'en')).toBe('just now');
  });

  it('returns "à l\'instant" for recent timestamps (fr)', () => {
    const now = new Date().toISOString();
    expect(formatRelativeTime(now, 'fr')).toBe("à l'instant");
  });

  it('returns minutes ago for timestamps within the hour', () => {
    const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
    expect(formatRelativeTime(fiveMinAgo, 'en')).toBe('5 min ago');
  });

  it('returns hours ago for timestamps within the day', () => {
    const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
    expect(formatRelativeTime(twoHoursAgo, 'en')).toBe('2h ago');
  });

  it('returns "yesterday" for 1 day ago', () => {
    const oneDayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
    expect(formatRelativeTime(oneDayAgo, 'en')).toBe('yesterday');
  });

  it('returns days ago for within a week', () => {
    const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
    expect(formatRelativeTime(threeDaysAgo, 'en')).toBe('3d ago');
  });
});
