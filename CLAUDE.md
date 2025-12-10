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

**Responsive strategy:**
- Desktop: 12-column CSS grid with stacks using `display: contents`
- Mobile (≤768px): Full-width horizontal swipe pages with pagination dots
- Stacks (`.intro-stack`, `.charts-stack-1`, etc.) group related cards

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
