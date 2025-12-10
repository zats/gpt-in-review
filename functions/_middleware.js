// Card-specific OG images (add entries as you create images)
const CARD_IMAGES = {
  // 'tarot-card': '/og-images/tarot.png',
  // 'streak': '/og-images/streak.png',
};

// Default OG image for all pages
const DEFAULT_OG_IMAGE = '/og-image.png';

const SITE_URL = 'https://gptinreview.com';
const SITE_TITLE = 'GPT in Review';
const SITE_DESCRIPTION = 'Reliving best memories with ChatGPT';

function getOgImageForCard(cardId) {
  if (cardId && CARD_IMAGES[cardId]) {
    return CARD_IMAGES[cardId];
  }
  return DEFAULT_OG_IMAGE;
}

function injectOgTags(html, url, ogImage) {
  const cardId = url.searchParams.keys().next().value || null;
  const fullImageUrl = `${SITE_URL}${ogImage}`;
  const fullPageUrl = cardId ? `${SITE_URL}?${cardId}` : SITE_URL;

  const ogTags = `
    <!-- Open Graph -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="${fullPageUrl}">
    <meta property="og:title" content="${SITE_TITLE}">
    <meta property="og:description" content="${SITE_DESCRIPTION}">
    <meta property="og:image" content="${fullImageUrl}">

    <!-- Twitter -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:url" content="${fullPageUrl}">
    <meta name="twitter:title" content="${SITE_TITLE}">
    <meta name="twitter:description" content="${SITE_DESCRIPTION}">
    <meta name="twitter:image" content="${fullImageUrl}">
  `;

  // Insert before </head>
  return html.replace('</head>', `${ogTags}</head>`);
}

export async function onRequest(context) {
  const { request, next } = context;
  const url = new URL(request.url);

  // Only intercept HTML requests to the root path
  if (url.pathname !== '/' && url.pathname !== '') {
    return next();
  }

  // Get the static HTML
  const response = await next();
  const html = await response.text();

  // Determine which OG image to use
  const cardId = url.searchParams.keys().next().value || null;
  const ogImage = getOgImageForCard(cardId);

  // Inject OG tags
  const modifiedHtml = injectOgTags(html, url, ogImage);

  const commitSha = context.env.CF_PAGES_COMMIT_SHA || 'unknown';
  return new Response(modifiedHtml, {
    headers: {
      'content-type': 'text/html;charset=UTF-8',
      'cache-control': 'public, max-age=31536000, immutable',
      'etag': `"${commitSha}"`,
      'x-deploy-sha': commitSha,
    },
  });
}
