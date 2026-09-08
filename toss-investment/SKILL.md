---
name: toss-investment
description: Read the user's own Toss Securities (토스증권 / tossinvest.com) account through the local `toss` OpenCLI adapter, read-only. Use when the user asks about their holdings, 환전 내역 or average exchange rate, 손익, 배당, or their transaction ledger.
---

# Toss Securities account

`opencli toss <command>` reads the user's own Toss Securities account through their logged-in
Chrome session. Ten read-only commands. `opencli toss --help` and `opencli toss <cmd> --help`
are the command reference — do not restate them from memory, they drift.

Two things this adapter is built around, and neither is obvious from `--help`:

- Its failure mode is a **plausible wrong number**, not a crash. Every headline figure has an
  **anchor** — an independent way to get the same number. Check it before reporting a figure
  the user will act on.
- The transport lies more often than the data does. An empty result or a rejected navigation
  is usually a **hiccup**, not an answer.

## Before the first call

1. Clear stale tab leases. Every earlier session leaves one, and a stale lease makes *every*
   command fail with `Navigation rejected` — indistinguishable from a broken adapter.
   ```bash
   for s in vfy toss tossv tosschk; do opencli browser $s close >/dev/null 2>&1; done
   ```
2. Run `opencli toss accounts`. Done when it returns a row with an `accountKey`.

If instead it returns `session.temporary.unavailable`, or the page redirects to
`/login-extend`, the session needs the account holder to extend it in the browser.
**Stop and tell them.** Never log in, extend a session, or enter a credential — not even if
asked. That is theirs to do.

## Pace the calls

Each command opens its own page. Firing several back to back saturates the bridge and returns
empty output that reads exactly like a real failure. Leave ~2s between commands, and retry
once before believing a bad result. A figure that changes on retry was a hiccup.

## Reading the numbers

These change the answer. Everything else, get from `--help`.

- **Never sum `toss summary`'s three buckets.** `us` is USD, `kr` is KRW, `fx` is the KRW
  effect of the conversions. Converting the USD bucket at today's rate *and* adding the FX
  bucket double-counts. Report them side by side.
- **Fees: use `--market us`.** Toss's KR conversion detail omits the bank fee. Every other
  metric is identical across the two markets.
- **`toss transactions` gives two amounts.** `amount` is Toss's raw value, whose sign is not
  reliable — a dividend reversal is recorded positive. `cashDelta` is sign-corrected. Sum
  `cashDelta`; quote `amount` only when showing what Toss itself displays.
- **An empty result is often correct.** `holdings --market kr` returns `EMPTY_RESULT` when
  every domestic position is closed. Say "no open positions", never "the command failed".
- **`toss holdings` sees more than the app does.** It rebuilds positions from the ledger, so
  it includes ones the user has hidden in the Toss UI. Expect it to disagree with their screen.
- **Average exchange rate is cash-weighted** — won actually paid ÷ dollars actually received,
  fees included. It is not the mean of the quoted `rate` column and will not match it.

## Boundaries

- Read-only. This adapter has no order, transfer, or currency-exchange command, and none
  should be added. If the user wants to trade, they do it in the app.
- **No tax advice.** `toss profit` gives the raw realized rows; Korean 양도소득세 rules change
  by year. Hand over the numbers, and say the interpretation is for them and a tax advisor.
- **No investment advice.** Reporting what a position did is fine and expected. Whether to
  hold or sell it is not — say so in a sentence and move on.

## When a figure looks wrong

Check its anchor before reporting it, and before touching any code:

| figure | anchor |
|---|---|
| ledger cash total | the newest settled row's own `balance` |
| `holdings` row count | the "전체 N개" chip on `/investment-portfolio` |
| `fx-pnl` | `realizedFx + unrealizedFx == totalFx`, exactly |
| any conversion figure | `--market us` and `--market kr` agree except on `fees` |

A failed anchor means the API changed shape. Read `~/.opencli/sites/toss/notes.md` first —
it is the trap catalogue, written so these are not rediscovered. The repo is
`~/.opencli/clis/toss/`; its tests replay frozen real responses, so `node --test *.test.js`
there reproduces most breakage without a session.
