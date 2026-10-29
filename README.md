# MW4 Discord notifier

GitHub Actions runs daily at 01:00 UTC = 10:00 Korea Standard Time.

## Required setup
1. Rotate the Discord webhook URL that was shared in chat. Do not commit its URL.
2. Repository Settings → Secrets and variables → Actions → New repository secret.
3. Add `DISCORD_WEBHOOK_URL` with the NEW Discord webhook URL.
4. To read X posts, also add `X_BEARER_TOKEN` from the X API developer portal.
5. Actions → **MW4 Discord News** → Run workflow to establish a quiet initial baseline.
6. On later runs, alerts are sent only for new content. Check Actions history for network/API errors.

**Limits:** X access requires API authorization and may cost money. The rule for nonofficial posts detects overlapping reports, **not independent factual verification**. Such notices are always labeled **유출·미확정**. First execution does not send previous items. Official patch changes are detected as page-level text changes, not detailed diff summaries. GitHub scheduled Actions may start later than the specified time.

This repository contains no credentials.
