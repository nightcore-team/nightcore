# Contributing to Nightcore

Thanks for taking the time to contribute. This document describes how to
report a bug properly and how to submit a pull request so it can be
reviewed quickly.

These are guidelines, not hard rules — but following them significantly
speeds up the review of your contribution.

## Before you do anything

The fastest way to reach the team directly is our Discord server: https://discord.gg/nDmYphcHk8. That's the place to discuss a feature idea, clarify
details before opening a PR, or just ask the developers something.

**Nightcore is developed according to the team's own roadmap, so we
generally don't accept pull requests that add new features** — they won't
be reviewed and will be closed regardless of how good the idea is. If you
have a feature idea, discuss it with the team directly (Discord) instead
of opening a PR.

A code contribution makes sense if it is:

- **A bug fix** — something behaves differently from what it's supposed
  to (an error, a crash, unexpected behavior, a resource leak, a race
  condition, etc.).
- **A documentation fix** — an inaccuracy or outdated description in the
  README or in comments.
- **A small refactor** directly tied to a bug fix (with no behavior
  change).

If you're not sure whether something is worth a PR, open an issue first
and describe the problem. We'll let you know whether it's worth fixing.

## I have a question, not a bug

The issue tracker isn't the place for questions like "how do I configure
this" or "why doesn't it work for me" (without a reproducible bug). Such
issues will be closed with a request to reach out on the team's Discord
instead.

## Filing a good bug report

Nightcore can be added to any server, so in most cases the person who
found a bug **doesn't have access to logs or any internal information
about the bot** — and we don't expect them to. You can report a bug in
two ways:

- **through the bot's built-in bug report command** (recommended — this
  way the report lands directly in the right channel for the team);
- **by messaging/pinging the team directly** on Discord.

You don't need a traceback, logs, or any technical details — a plain,
**written description** is enough. What matters most is that it's clear
what actually broke. A good report usually includes:

1. **What you were doing.** Which command or action you performed in the
   bot (e.g. "used `/clan invite`", "clicked a button in a ticket",
   "bought an item in the shop").
2. **What you expected to happen.** What the result should have been.
3. **What actually happened.** What went wrong — the bot didn't respond,
   showed an error, did something else, the action was duplicated, etc.
4. **A screenshot, if possible.** A screenshot of the bot's message,
   error, or the odd behavior speeds things up a lot — but it's not
   required if the written description is clear enough.
5. **How often it happens** (if you know): always, sometimes, once.

If there isn't enough information to work with, the team will ask for
more details in the same channel/thread.

## Submitting a Pull Request

### Important: no "AI slop"

**We don't accept PRs where it's clear the author didn't actually
understand the code they're changing** and just generated a patch with
Claude Code, Copilot, ChatGPT, Cursor, Codex, etc. without reviewing or
understanding it.

This isn't a blanket "did you touch an AI tool at all" rule — it's about
the quality and intentionality of the change. Signs that will get a PR
closed without review:

- The change ignores existing patterns in the project (e.g. skipping the
  Unit of Work pattern / `FOR UPDATE` locks where the surrounding code
  clearly uses them, or inventing its own approach to transactions or
  error handling instead of following what the project already does).
- The change is much broader than the fix requires — refactoring nearby
  code, renaming variables, "improving" style you weren't asked to touch.
- The PR description reads like generic, "marketing-style" text with no
  specifics about this particular bug (can't explain why the bug
  happened or why this particular fix was chosen).
- The author can't explain, in their own words, what caused the bug when
  asked in the comments.

If you use AI tools as an aid, that's your business — but **the final
result has to clearly show you understand this specific part of the
code**: it follows the style and patterns already used in the project,
touches only what's relevant to the bug, and you can explain every line
of the change. If a reviewer recognizes a typical "AI diff" with no
signs of understanding the context, the PR will be closed without
further discussion.

### Step 1. Fork the repository

Click **Fork** in the top-right corner of the repository page
(https://github.com/nightcore-team/nightcore) to get your own copy under
your account.

### Step 2. Clone your fork

```
git clone https://github.com/<your-username>/nightcore.git
cd nightcore
```

Add the original repository as `upstream` so you can easily pull in
fresh changes later:

```
git remote add upstream https://github.com/nightcore-team/nightcore.git
```

### Step 3. Create a dedicated branch

**Don't work on `main`.** Create a branch for your specific fix:

```
git checkout main
git pull upstream main
git checkout -b fix/short-description
```

Branch name examples: `fix/ticket-double-close`,
`fix/clan-invite-race`, `docs/env-example-typo`. Use the same type as in
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
(`fix/`, `docs/`, `refactor/`) — see the next step.

One branch, one problem. Don't mix several unrelated fixes in a single
PR.

### Step 4. Make the change

- Stay focused: the PR should solve **one specific problem**, without
  side changes "while I'm in here" (aside from obvious nearby typos).
- Follow the coding style already used in the project. We use
  [Ruff](https://docs.astral.sh/ruff/) for linting and formatting. The
  linter and formatter rules are pinned in `pyproject.toml` at the root
  of the repository, so they apply automatically locally — nothing to
  configure manually.
- If your change touches database models, don't forget an Alembic
  migration (`make migration`) if the table structure changed.
- Test your change locally before opening a PR (see the main README for
  how to run the bot locally).

#### Checks to run

```
make format
make lint
```

Before opening a PR, run `make format` and then `make lint`, and make
sure both pass without errors.

### Step 5. Commit your changes

We follow [Conventional
Commits](https://www.conventionalcommits.org/en/v1.0.0/). Commit message
format:

```
<type>[optional scope]: <short description>

[optional longer description]

[optional footer, e.g. Fixes #123]
```

- **Type** — required, one of:
  - `fix` — a bug fix (most of your PRs will be this type);
  - `docs` — documentation-only changes;
  - `refactor` — a code change with no behavior impact (no new
    functionality and no specific bug fix);
  - `test` — adding or fixing tests;
  - `chore` — technical housekeeping unrelated to bot logic (e.g.
    dependency bumps).
  - Don't use `feat` — we don't accept features through external PRs
    (see above).
- **Scope** (optional, in parentheses) — the module/feature from
  `src/nightcore/features/` or `events/` that the change touches:
  `fix(tickets): ...`, `fix(moderation): ...`, `fix(clans): ...`.
- **Short description** — present tense, imperative mood (`fix ticket
  count race`, not `fixed`/`fixes`), no trailing period, under 72
  characters including the type and scope.
- **Footer** — reference issues in shorthand: `Fixes #123`, `Refs #123`,
  not the full URL.

Example of a good commit:

```
fix(tickets): fix ticket count race on rapid open/close

Ticket counter could be incremented twice if a user opened
two tickets within the same event loop tick, because the
count check and the insert weren't wrapped in the same
transaction. Locks the config row with FOR UPDATE before
checking the limit.

Fixes #142
```

The same format applies to the **PR title itself** — it should also look
like `fix(tickets): fix ticket count race on rapid open/close`.

### Step 6. Push the branch and open a PR

```
git push origin fix/short-description
```

Then click **Compare & pull request** on GitHub. The PR description will
load automatically from our template
(`.github/PULL_REQUEST_TEMPLATE.md`) — just fill in the fields, no need
to copy anything manually. Format the PR title the same way as the
commit title (see step 5).

### What happens next

- A reviewer may ask for changes — that's a normal part of the process,
  not a rejection.
- If your commits don't follow the style guidelines above, we'll usually
  fix that ourselves during a rebase, but it's better to get it right the
  first time to save everyone time.
- A PR that sits without a response from the author to reviewer feedback
  for a long time may be closed.

## Thank you

Even a small, targeted fix is real help to the project. What matters
most is that the change is clear, scoped to a single issue, and written
by you personally.