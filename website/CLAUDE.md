# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Static website for visualizing ChatGPT usage data. Displays conversation statistics, messaging patterns, topic analysis, and fun metrics in a responsive bento-grid layout.

## Development

**Serve locally:**
```bash
python -m http.server 8000
# or
npx serve
```

Open `http://localhost:8000` in browser. The site loads `data.json` via fetch, so a local server is required.

## Architecture

### File Structure
- `index.html` - Main layout with bento grid sections and shimmer placeholders
- `script.js` - UI orchestration: theme switching, mobile pagination, share buttons, scroll tracking
- `charts.js` - Data visualization: D3.js charts, word clouds, static content rendering
- `styles.css` - Responsive CSS with mobile-first swipeable card layout
- `data.json` - Pre-computed statistics (generated externally)

### Key Design Patterns

**Two-script separation:**
- `script.js` handles DOM/UI concerns (pagination, URL state, theming)
- `charts.js` handles data fetching and all D3/WordCloud rendering

**Responsive strategy - Desktop vs Mobile:**

Desktop (>768px):
- 12-column CSS grid "bento box" layout
- Cards arranged in visual groups using stack containers
- Stacks (`.intro-stack`, `.charts-stack-1`, `.vibes-top-stack`, etc.) use flexbox to position related cards
- Share buttons appear on hover for each card
- Scroll position updates URL query param for deep linking

Mobile (≤768px):
- Converts to horizontally-swipeable paginated view
- Each "page" is a full-viewport card with pagination dots at bottom
- Some stacks combine multiple cards into a single page (e.g., `.intro-stack`, `.stats-stack`)
- Other stacks explode into separate pages (e.g., `.vibes-top-stack` splits nutrition, emoji, tarot into 3 pages)
- Stack containers use `display: contents` to flatten hierarchy for swipe navigation
- Card borders/shadows stripped for cleaner full-screen appearance
- Keyboard arrows navigate between pages
- Swipe position updates URL query param

**Theme support:**
- Uses CSS custom properties (`--bg`, `--accent`, etc.)
- `data-theme` attribute on `<html>` toggles light/dark
- Charts re-render on theme change via MutationObserver

**Shimmer loading:**
- HTML contains `.shimmer` placeholders
- `charts.js` replaces shimmers with actual content after `data.json` loads

### Chart Types (all in charts.js)
- Bar charts: `renderHourChart`, `renderDayChart`, `renderMonthChart`
- Area chart: `renderTimelineChart`
- Streamgraph: `renderStreamgraph`
- Mirror chart: `renderFrustrationChart`
- Word clouds: `renderFrustrationCloud`, `renderEmojiClouds` (uses wordcloud2.js)

### External Dependencies (via CDN)
- D3.js v7 - charting
- wordcloud2.js - word clouds
- Google Fonts: Inter, Space Grotesk

## Maintenance Notes

### CSS Breakpoints & Synchronization

The site has three layout breakpoints that must be kept in sync:

1. **Desktop (>1024px)** - 12-column grid, stacks use `display: contents`
2. **Tablet (769px-1024px)** - 6-column grid, adjusted card spans
3. **Mobile (≤768px)** - Horizontal swipe pagination, full-viewport cards

**When modifying styles, check all three breakpoints.** Common items that need syncing:
- Card grid column assignments (tablet has different spans than desktop)
- Stack container display modes (flex on desktop/tablet, `display: contents` on mobile)
- Special background cards (streak, energy, water, emoji) - styling applies in all breakpoints
- Chart edge-to-edge negative margins (mobile only)

### Mobile Pagination Card Order

Mobile pagination in `script.js` collects cards in DOM order. The order is determined by:

1. How elements appear in `index.html`
2. How `display: contents` flattens nested stacks

**Current mobile page order:**
1. Title card
2. Tarot card (from vibes-top-stack)
3. Nutrition card (from vibes-right-stack)
4. Emoji card (from vibes-right-stack)
5. Frustration stack (frustration chart + word cloud combined)
6. Intro stack (first conversation + overview combined)
7. Stats stack (longest convo, longest msg, streak combined)
8. Charts stack 1 (hourly + daily combined)
9. Charts stack 2 (monthly + timeline combined)
10. Perspective stack 1 (words, pages, war&peace, CVS combined)
11. Perspective stack 2 (tokens, energy, water combined)
12. Topics stack (top topics + streamgraph combined)
13. API key card

**If you move bento boxes in index.html:**
- The mobile pagination order will change automatically
- Update this list in CLAUDE.md
- Test mobile swipe navigation to verify expected order
- Check that URL query params (`?cardId`) still navigate correctly

### Edge-to-Edge Charts on Mobile

Charts extend to screen edges using negative margins:
```css
.some-chart {
  margin-left: -1.25rem;
  margin-right: -1.25rem;
  width: calc(100% + 2.5rem);
}
```

Stacks containing edge-to-edge charts need:
- `overflow-x: hidden` on the stack
- `padding: X 0` (no horizontal padding on stack)
- `padding: X 1.25rem` on cards inside the stack

Currently applied to: charts-stack-1, charts-stack-2, topics-stack, frustration-stack

### Special Background Cards

Cards with colored backgrounds need extra attention:
- `.card-streak` - orange background
- `.card-energy` - amber background
- `.card-water` - sky blue background
- `.card-emojis` - black/white background (inverts in dark mode)

On mobile, these extend edge-to-edge with negative margins.
Share buttons on these cards match the card background color.
