# UI Design Guide — Indian Alpha Terminal

> The interface must feel like a **techy, dark trading terminal** — not a
> consumer fintech app. Dense, sharp, monospaced numbers, near-black surfaces.
> Color is almost entirely greyscale; the **only** hues that carry meaning are
> **green (up / buy / pass)** and **red (down / sell / veto)**.

## 1. Principles

- **Dark-first, single theme.** Near-black background, layered greys for panels. No light mode in the terminal.
- **Greyscale carries structure; red/green carry signal.** Never use blue/purple/orange as decoration. If a pixel is colored, it means something.
- **Monospace for all numbers.** Prices, %, quantities, probabilities, timestamps — tabular, aligned, monospaced. Sans-serif only for prose/labels.
- **Sharp, not soft.** Thin 1px borders, minimal radius (0–4px), no drop shadows, no gradients. Grid lines over cards.
- **Dense but legible.** Small type, tight rows, generous data per screen — like a Bloomberg/TradingView panel, not a marketing page.
- **Every number is traceable.** Hover/click reveals data version + timestamp (per phase-plan §6.6 acceptance).

## 2. Color tokens

Greyscale ramp (black → white) plus the two semantic accents. Use CSS variables so the whole app themes from one place.

```css
:root {
  /* Surfaces — near-black, layered */
  --bg:          #0a0a0a;   /* app background            */
  --panel:       #101012;   /* panels / cards            */
  --panel-2:     #16161a;   /* raised / hover panel      */
  --elevated:    #1c1c22;   /* modals, popovers          */

  /* Borders / grid — grey shades */
  --border:      #24242a;   /* default hairline border   */
  --border-soft: #1b1b20;   /* subtle divider            */
  --grid:        #202028;   /* chart grid lines          */

  /* Text — white through grey */
  --text:        #f4f4f5;   /* primary text / live nums  */
  --text-muted:  #a1a1aa;   /* secondary labels          */
  --text-dim:    #6b6b74;   /* tertiary / disabled       */

  /* Semantic — the ONLY meaningful hues */
  --up:          #16c784;   /* gain / BUY / long / PASS   */
  --up-dim:      #0e7a52;   /* muted up (bars, fills)     */
  --down:        #ea3943;   /* loss / SELL / short / VETO */
  --down-dim:    #9e2a30;   /* muted down                */
  --flat:        #a1a1aa;   /* unchanged / HOLD / neutral */

  /* Non-semantic status greys (warnings stay greyscale, not amber) */
  --warn:        #d4d4d8;   /* REVIEW / caution: bright grey, not orange */
  --focus-ring:  #3a3a44;   /* keyboard focus outline    */
}
```

**Semantic mapping (fixed, do not improvise):**

| Meaning | Token | Notes |
|---|---|---|
| Price up / BUY / long / risk PASS | `--up` green | |
| Price down / SELL / short / risk VETO | `--down` red | |
| HOLD / NO_TRADE / unchanged | `--flat` grey | Neutral, never green/red |
| REVIEW / warning / stale data | `--warn` bright grey | Greyscale, **not** amber/yellow |
| Structure, chrome, everything else | grey ramp | |

## 3. Typography

```css
--font-mono: "JetBrains Mono", "Geist Mono", ui-monospace, "SF Mono", Menlo, monospace;
--font-sans: "Geist", "Inter", ui-sans-serif, system-ui, sans-serif;
```

- Numbers, tickers, timestamps, code, IDs → `--font-mono`, `font-variant-numeric: tabular-nums`.
- Labels, thesis prose, bull/bear text → `--font-sans`.
- Scale: 11px (dense tables) · 12px (default) · 13–14px (body) · 16–20px (headline numbers). Avoid anything large/marketing-sized.

## 4. Components

- **Candle chart** — TradingView Lightweight Charts. Up candles `--up`, down candles `--down`, wicks slightly dimmed, grid `--grid`, crosshair `--text-dim`. Volume bars `--up-dim`/`--down-dim`.
- **Watchlist / scanner rows** — monospace, right-aligned numbers; % change colored `--up`/`--down`; row hover `--panel-2`; 1px `--border-soft` dividers.
- **AI floor panel** — agent name + status glyph. Done `✓` `--up`, partial `~` `--flat`, failed `✕` `--down`. Bull row tinted faint green, Bear row faint red, everything else grey.
- **Recommendation card** — action badge: BUY green, SELL red, HOLD/NO_TRADE grey outline. Risk verdict PASS green / VETO red / REVIEW bright-grey. All figures monospace.
- **Buttons** — flat, 1px border, no fill by default; hover raises to `--panel-2`. No colored CTA buttons except a destructive/confirm which may use `--down`.
- **Badges/tags** — greyscale pills with `--border`; colored only when semantic.

## 5. Hard rules

- No order-submit / buy-now button anywhere — manual execution only (matches non-negotiables).
- Never encode meaning in color alone — pair green/red with a glyph, sign (`+`/`−`), or label for accessibility.
- No decorative gradients, glows, or non-greyscale brand colors.
- A vetoed candidate must be visually distinct and can never render styled as an active recommendation.
- Stale/partial data gets a visible greyscale "STALE" tag and dims affected numbers to `--text-dim`.
