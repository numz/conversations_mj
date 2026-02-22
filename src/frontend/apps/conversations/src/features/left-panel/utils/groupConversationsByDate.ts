import { ChatConversation } from '@/features/chat/types';

export type TimeGroup =
  | 'today'
  | 'yesterday'
  | 'last7days'
  | 'last30days'
  | 'older';

export interface GroupedConversations {
  group: TimeGroup;
  conversations: ChatConversation[];
}

/**
 * Get the time group for a given date
 */
function getTimeGroup(date: Date): TimeGroup {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const last7days = new Date(today);
  last7days.setDate(last7days.getDate() - 7);
  const last30days = new Date(today);
  last30days.setDate(last30days.getDate() - 30);

  const conversationDate = new Date(
    date.getFullYear(),
    date.getMonth(),
    date.getDate(),
  );

  if (conversationDate >= today) {
    return 'today';
  } else if (conversationDate >= yesterday) {
    return 'yesterday';
  } else if (conversationDate >= last7days) {
    return 'last7days';
  } else if (conversationDate >= last30days) {
    return 'last30days';
  } else {
    return 'older';
  }
}

/**
 * Group conversations by time period
 */
export function groupConversationsByDate(
  conversations: ChatConversation[],
): GroupedConversations[] {
  const groups: Record<TimeGroup, ChatConversation[]> = {
    today: [],
    yesterday: [],
    last7days: [],
    last30days: [],
    older: [],
  };

  conversations.forEach((conversation) => {
    const date = new Date(conversation.updated_at);
    const group = getTimeGroup(date);
    groups[group].push(conversation);
  });

  const orderedGroups: TimeGroup[] = [
    'today',
    'yesterday',
    'last7days',
    'last30days',
    'older',
  ];

  return orderedGroups
    .filter((group) => groups[group].length > 0)
    .map((group) => ({
      group,
      conversations: groups[group],
    }));
}

/**
 * Get the translation key for a time group
 */
export function getTimeGroupLabel(group: TimeGroup): string {
  switch (group) {
    case 'today':
      return 'Today';
    case 'yesterday':
      return 'Yesterday';
    case 'last7days':
      return 'Last 7 days';
    case 'last30days':
      return 'Last 30 days';
    case 'older':
      return 'Older';
  }
}

/**
 * Format a relative time string for a conversation
 */
export function formatRelativeTime(dateString: string, locale = 'fr'): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) {
    return locale === 'fr' ? "à l'instant" : 'just now';
  } else if (diffMins < 60) {
    return locale === 'fr' ? `il y a ${diffMins} min` : `${diffMins} min ago`;
  } else if (diffHours < 24) {
    return locale === 'fr' ? `il y a ${diffHours}h` : `${diffHours}h ago`;
  } else if (diffDays === 1) {
    return locale === 'fr' ? 'hier' : 'yesterday';
  } else if (diffDays < 7) {
    return locale === 'fr' ? `il y a ${diffDays}j` : `${diffDays}d ago`;
  } else {
    return date.toLocaleDateString(locale, {
      day: 'numeric',
      month: 'short',
    });
  }
}
