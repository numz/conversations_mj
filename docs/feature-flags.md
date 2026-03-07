# Custom Feature Flags

Conversations supports custom feature flags to enable or disable optional features
without code changes. Flags are configured via environment variables on the backend
and exposed to the frontend via the `/api/v1.0/config/` endpoint in the `feature_flags_custom` object.

## How it works

### Backend

Each feature flag is a `BooleanValue` setting in `src/backend/conversations/settings.py`.
It is exposed to the frontend via the `ConfigView` in `src/backend/core/api/viewsets.py`:

```python
dict_settings["feature_flags_custom"] = {
    "reasoning_box_enabled": settings.REASONING_BOX_ENABLED,
    "enable_table_export": settings.ENABLE_TABLE_EXPORT,
    # ... other flags
}
```

### Frontend

The `useFeatureFlags()` hook (from `@/core/config/api`) reads flags from the config API response:

```typescript
import { useFeatureFlags } from '@/core/config/api';

const featureFlags = useFeatureFlags();

if (featureFlags.reasoning_box_enabled) {
  // render feature
}
```

Flags default to `false` when not present in the API response, preserving upstream behavior.

## Available Flags

| Flag                            | Env Variable                     | Default | Description                                                            |
|---------------------------------|----------------------------------|---------|------------------------------------------------------------------------|
| `reasoning_box_enabled`         | `REASONING_BOX_ENABLED`          | `true`  | Show a collapsible reasoning/thinking box in chat messages             |
| `enable_table_export`           | `ENABLE_TABLE_EXPORT`            | `true`  | Add CSV export button on markdown tables in chat                       |
| `prompt_suggestions_enabled`    | `PROMPT_SUGGESTIONS_ENABLED`     | `true`  | Show clickable prompt suggestion cards on empty chat                   |
| `conversation_grouping_enabled` | `CONVERSATION_GROUPING_ENABLED`  | `true`  | Group conversations by date in the left panel                          |
| `inline_rename_enabled`         | `INLINE_RENAME_ENABLED`          | `true`  | Inline conversation renaming with typewriter animation                 |
| `local_feedback_enabled`        | `LOCAL_FEEDBACK_ENABLED`         | `false` | Persist feedback locally in DB with comment/categories modal           |

## Adding a New Feature Flag

1. Add the setting in `src/backend/conversations/settings.py`:
   ```python
   MY_FEATURE_ENABLED = values.BooleanValue(
       default=True, environ_name="MY_FEATURE_ENABLED", environ_prefix=None,
   )
   ```

2. Expose it in `src/backend/core/api/viewsets.py` inside the `feature_flags_custom` dict:
   ```python
   dict_settings["feature_flags_custom"] = {
       # ...existing flags...
       "my_feature_enabled": settings.MY_FEATURE_ENABLED,
   }
   ```

3. Use it in the frontend:
   ```typescript
   const featureFlags = useFeatureFlags();
   if (featureFlags.my_feature_enabled) {
     // ...
   }
   ```

## See Also

- [Environment Variables](env.md) - All configuration variables
- [Architecture](architecture.md) - System architecture overview
