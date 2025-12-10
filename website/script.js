(function() {
  'use strict';

  // Theme - always follow system preference
  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
  }

  setTheme(getSystemTheme());

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    setTheme(e.matches ? 'dark' : 'light');
  });

  // Mobile Pagination State (module-level to avoid duplicates)
  let currentIndex = 0;
  let keyboardHandler = null;
  let mobileCards = []; // Store cards for anchor navigation

  // Mobile Pagination
  function initMobilePagination() {
    const main = document.querySelector('.bento');
    const isMobile = window.innerWidth <= 768;

    // Get all swipeable pages, handling stacks that use display:contents on mobile
    const cards = [];
    Array.from(main.children).forEach(el => {
      // Skip section headers (hidden on mobile)
      if (el.classList.contains('section-header')) return;

      // emoji-nutrition-stack uses display:contents on mobile, so expand its children
      if (el.classList.contains('emoji-nutrition-stack')) {
        Array.from(el.children).forEach(child => {
          if (child.classList.contains('card')) {
            cards.push(child);
          }
        });
        return;
      }

      // vibes-top-stack uses display:contents on mobile, expand its children recursively
      if (el.classList.contains('vibes-top-stack')) {
        Array.from(el.children).forEach(child => {
          if (child.classList.contains('card')) {
            cards.push(child);
          }
          if (child.classList.contains('vibes-right-stack')) {
            // vibes-right-stack also uses display:contents, expand its cards
            Array.from(child.children).forEach(grandchild => {
              if (grandchild.classList.contains('card')) {
                cards.push(grandchild);
              }
            });
          }
        });
        return;
      }

      // Include cards and stacks that stay combined
      if (el.classList.contains('card') ||
          el.classList.contains('intro-stack') ||
          el.classList.contains('stats-stack') ||
          el.classList.contains('charts-stack-1') ||
          el.classList.contains('charts-stack-2') ||
          el.classList.contains('perspective-stack-1') ||
          el.classList.contains('perspective-stack-2') ||
          el.classList.contains('topics-stack') ||
          el.classList.contains('frustration-stack')) {
        cards.push(el);
      }
    });

    // Store for anchor navigation
    mobileCards = cards;

    // Clean up existing pagination elements
    const existingPagination = document.querySelector('.pagination');
    if (existingPagination) existingPagination.remove();

    // Remove old keyboard handler if exists
    if (keyboardHandler) {
      document.removeEventListener('keydown', keyboardHandler);
      keyboardHandler = null;
    }

    if (!isMobile) {
      main.classList.remove('paginated');
      return;
    }

    main.classList.add('paginated');

    // Create pagination dots
    const pagination = document.createElement('div');
    pagination.className = 'pagination';
    cards.forEach((_, i) => {
      const dot = document.createElement('button');
      dot.className = 'dot' + (i === 0 ? ' active' : '');
      dot.setAttribute('aria-label', `Go to card ${i + 1}`);
      dot.addEventListener('click', () => scrollToCard(i));
      pagination.appendChild(dot);
    });
    document.body.appendChild(pagination);

    function scrollToCard(index) {
      if (index < 0 || index >= cards.length) return;
      currentIndex = index;
      // Get the actual scroll position of the target card
      // Use getBoundingClientRect relative to the scroll container for accurate position
      const targetCard = cards[index];
      const mainRect = main.getBoundingClientRect();
      const cardRect = targetCard.getBoundingClientRect();
      const scrollLeft = main.scrollLeft + (cardRect.left - mainRect.left);
      main.scrollTo({ left: scrollLeft, behavior: 'smooth' });
      updateUI();
    }

    // Expose scrollToCard for anchor navigation
    window.scrollToMobileCard = scrollToCard;

    function updateUI() {
      // Update dots
      pagination.querySelectorAll('.dot').forEach((dot, i) => {
        dot.classList.toggle('active', i === currentIndex);
      });
    }

    // Update on scroll
    let scrollTimeout;
    main.addEventListener('scroll', () => {
      clearTimeout(scrollTimeout);
      scrollTimeout = setTimeout(() => {
        const mainRect = main.getBoundingClientRect();
        // Find the card closest to current scroll position (center of viewport)
        let closestIndex = 0;
        let closestDistance = Infinity;
        cards.forEach((card, i) => {
          const cardRect = card.getBoundingClientRect();
          const distance = Math.abs(cardRect.left - mainRect.left);
          if (distance < closestDistance) {
            closestDistance = distance;
            closestIndex = i;
          }
        });
        currentIndex = closestIndex;
        updateUI();
        updateUrlParam(cards[closestIndex]);
      }, 50);
    });

    // Keyboard navigation - store handler so we can remove it later
    keyboardHandler = (e) => {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        e.stopPropagation();
      }
      if (e.key === 'ArrowLeft') {
        scrollToCard(currentIndex - 1);
      }
      if (e.key === 'ArrowRight') {
        scrollToCard(currentIndex + 1);
      }
    };
    document.addEventListener('keydown', keyboardHandler);

    updateUI();

    // Handle initial card param on mobile
    if (window.location.search.slice(1)) {
      handleCardNavigation();
    }
  }

  // Update URL query param without triggering navigation
  let isUpdatingUrl = false;
  function updateUrlParam(element) {
    if (!element || !element.id) return;
    const currentCard = window.location.search.slice(1); // Remove '?'
    if (currentCard === element.id) return;

    isUpdatingUrl = true;
    const url = `${window.location.pathname.replace(/\/$/, '')}?${element.id}`;
    history.replaceState(null, '', url);
    // Reset flag after a short delay
    setTimeout(() => { isUpdatingUrl = false; }, 100);
  }

  // Card Navigation (from ?cardId query param)
  function handleCardNavigation() {
    // Skip if we're the ones updating the URL
    if (isUpdatingUrl) return;
    const cardId = window.location.search.slice(1); // Remove '?'
    if (!cardId) return;

    const targetElement = document.getElementById(cardId);
    if (!targetElement) return;

    const isMobile = window.innerWidth <= 768;

    if (isMobile) {
      // Find which mobile page contains this element
      let pageIndex = -1;

      // Check if the target is a mobile page itself
      pageIndex = mobileCards.findIndex(card => card.id === cardId);

      // If not found, check if the target is inside a mobile page
      if (pageIndex === -1) {
        pageIndex = mobileCards.findIndex(card => card.contains(targetElement));
      }

      if (pageIndex !== -1 && window.scrollToMobileCard) {
        window.scrollToMobileCard(pageIndex);
      }
    } else {
      // Desktop: smooth scroll to element
      targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  // Share button functionality
  function initShareButtons() {
    const isMobile = window.innerWidth <= 768;
    if (isMobile) return;

    // Remove existing share buttons
    document.querySelectorAll('.share-btn').forEach(btn => btn.remove());

    // Get all cards with IDs
    const cards = document.querySelectorAll('.card[id]');

    const shareSvg = `<svg viewBox="0 0 24 24"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>`;

    cards.forEach(card => {
      const btn = document.createElement('button');
      btn.className = 'share-btn';
      btn.innerHTML = shareSvg;
      btn.setAttribute('aria-label', 'Share this card');

      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        const url = `${window.location.origin}${window.location.pathname.replace(/\/$/, '')}?${card.id}`;

        // Build share text: "GPT in Review: <section> - <card>" or "GPT in Review: <card>" or "GPT in Review"
        const cardTitle = card.querySelector('.card-label')?.textContent?.trim();

        // Find preceding section header
        let sectionTitle = null;
        let el = card.previousElementSibling;
        while (el) {
          if (el.classList.contains('section-header')) {
            sectionTitle = el.querySelector('.section-title')?.textContent?.trim();
            break;
          }
          el = el.previousElementSibling;
        }

        let shareText = 'GPT in Review';
        if (sectionTitle && cardTitle) {
          shareText = `GPT in Review: ${sectionTitle} - ${cardTitle}`;
        } else if (cardTitle) {
          shareText = `GPT in Review: ${cardTitle}`;
        }

        const twitterUrl = `https://x.com/intent/tweet?url=${encodeURIComponent(url)}&text=${encodeURIComponent(shareText)}`;

        // Try native share first, fall back to X.com
        if (navigator.share) {
          // Pre-open window SYNCHRONOUSLY to avoid popup blocker after async
          const fallbackWindow = window.open('about:blank', '_blank');
          const t0 = performance.now();

          try {
            await navigator.share({ title: shareText, url });
            // Success - close the fallback window
            if (fallbackWindow) fallbackWindow.close();
            return;
          } catch (err) {
            // If user cancelled (took >500ms), close window and don't fall back
            if (err.name === 'AbortError' && (performance.now() - t0) > 500) {
              if (fallbackWindow) fallbackWindow.close();
              return;
            }
            // Share blocked/failed - redirect fallback window to Twitter
            if (fallbackWindow) {
              fallbackWindow.location.href = twitterUrl;
              return;
            }
          }
        }

        // No navigator.share - open directly
        window.open(twitterUrl, '_blank');
      });

      card.appendChild(btn);
    });
  }

  function copyToClipboard(text, btn, card) {
    navigator.clipboard.writeText(text).then(() => {
      // Show checkmark on button
      const originalSvg = btn.innerHTML;
      btn.innerHTML = `<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`;

      // Show toast notification
      showToast('Link copied to clipboard');

      setTimeout(() => {
        btn.innerHTML = originalSvg;
      }, 1500);
    });
  }

  function showToast(message) {
    // Remove existing toast
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    // Remove after delay
    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 2000);
  }

  // Desktop scroll tracking with Intersection Observer
  let desktopObserver = null;
  function initDesktopScrollTracking() {
    const isMobile = window.innerWidth <= 768;

    // Clean up existing observer
    if (desktopObserver) {
      desktopObserver.disconnect();
      desktopObserver = null;
    }

    if (isMobile) return;

    // Get all elements with IDs that are cards or stacks
    const trackableElements = document.querySelectorAll('[id].card, [id].intro-stack, [id].stats-stack, [id].charts-stack-1, [id].charts-stack-2, [id].perspective-stack-1, [id].perspective-stack-2, [id].topics-stack, [id].frustration-stack');

    desktopObserver = new IntersectionObserver((entries) => {
      // Find the entry that's most visible and near the top
      let topVisibleEntry = null;
      let topPosition = Infinity;

      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const rect = entry.boundingClientRect;
          // Prioritize elements near the top of the viewport
          if (rect.top >= -100 && rect.top < topPosition) {
            topPosition = rect.top;
            topVisibleEntry = entry;
          }
        }
      });

      if (topVisibleEntry && topVisibleEntry.target.id) {
        updateUrlParam(topVisibleEntry.target);
      }
    }, {
      rootMargin: '-10% 0px -70% 0px', // Trigger when element is in top 30% of viewport
      threshold: 0
    });

    trackableElements.forEach(el => desktopObserver.observe(el));
  }

  // Initialize
  document.addEventListener('DOMContentLoaded', () => {
    const hasCardParam = window.location.search.slice(1);
    const isMobile = window.innerWidth <= 768;

    initMobilePagination();
    initShareButtons();

    // Handle card navigation on page load
    if (hasCardParam) {
      // Navigate to the card first, then start tracking
      setTimeout(() => {
        handleCardNavigation();
        // Start scroll tracking after navigation completes
        setTimeout(() => {
          initDesktopScrollTracking();
        }, 500);
      }, 100);
    } else {
      initDesktopScrollTracking();
    }
  });

  // Listen for popstate (back/forward navigation)
  window.addEventListener('popstate', handleCardNavigation);

  // Re-init on resize
  let resizeTimeout;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
      initMobilePagination();
      initDesktopScrollTracking();
      initShareButtons();
    }, 200);
  });

})();
