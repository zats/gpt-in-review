(function() {
  'use strict';

  // ═══════════════════════════════════════════════════════════════════════════
  // Render Static Content (replaces shimmers)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderStaticContent(data) {
    // First conversation
    const firstDate = document.getElementById('first-date');
    if (firstDate) firstDate.textContent = data.firstConversation.date;

    const firstChat = document.getElementById('first-chat-messages');
    if (firstChat) {
      firstChat.innerHTML = data.firstConversation.messages.map(msg =>
        `<div class="msg ${msg.role}">${msg.text}</div>`
      ).join('');
    }

    const firstDuration = document.getElementById('first-duration');
    if (firstDuration) firstDuration.innerHTML = `First conversation lasted <strong>${data.firstConversation.duration}</strong>`;

    // Overview
    const overviewTotal = document.getElementById('overview-total');
    if (overviewTotal) overviewTotal.textContent = data.overview.totalMessages.toLocaleString();

    const overviewLabel = document.getElementById('overview-label');
    if (overviewLabel) overviewLabel.innerHTML = `messages across <strong>${data.overview.totalConversations.toLocaleString()}</strong> conversations`;

    const overviewUser = document.getElementById('overview-user');
    if (overviewUser) overviewUser.textContent = data.overview.userMessages.toLocaleString();

    const overviewAssistant = document.getElementById('overview-assistant');
    if (overviewAssistant) overviewAssistant.textContent = data.overview.assistantMessages.toLocaleString();

    const overviewAvg = document.getElementById('overview-avg');
    if (overviewAvg) overviewAvg.textContent = data.overview.avgPerChat;

    // Longest conversation
    const longestConvoVal = document.getElementById('longest-convo-val');
    if (longestConvoVal) longestConvoVal.textContent = data.longestConversation.value;

    const longestConvoTitle = document.getElementById('longest-convo-title');
    if (longestConvoTitle) longestConvoTitle.textContent = `"${data.longestConversation.title}"`;

    // Longest message
    const longestMsgVal = document.getElementById('longest-msg-val');
    if (longestMsgVal) longestMsgVal.textContent = data.longestMessage.value;

    const longestMsgTitle = document.getElementById('longest-msg-title');
    if (longestMsgTitle) longestMsgTitle.textContent = `"${data.longestMessage.title}"`;

    // Streak (calculated from ISO dates)
    const streakVal = document.getElementById('streak-val');
    const streakDates = document.getElementById('streak-dates');
    if (streakVal && streakDates && data.streak.from) {
      const fromDate = new Date(data.streak.from + 'T00:00:00');
      const toDate = data.streak.to
        ? new Date(data.streak.to + 'T00:00:00')
        : new Date();

      // Calculate days difference
      const diffMs = toDate - fromDate;
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      // Format the value
      streakVal.textContent = `${diffDays} days`;

      // Format dates for display
      const formatDate = (date) => {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      };
      const formatYear = (date) => date.getFullYear();

      if (data.streak.to) {
        // Completed streak: "Jun 11 → Dec 1, 2025"
        const fromStr = formatDate(fromDate);
        const toStr = formatDate(toDate);
        const year = formatYear(toDate);
        streakDates.textContent = `${fromStr} → ${toStr}, ${year}`;
      } else {
        // Ongoing streak: "Jun 11, 2025 → ongoing"
        const fromStr = formatDate(fromDate);
        const year = formatYear(fromDate);
        streakDates.textContent = `${fromStr}, ${year} → ongoing`;
      }
    }

    // Perspective section
    const totalWords = document.getElementById('total-words-val');
    if (totalWords) totalWords.textContent = data.perspective.totalWords;

    const bookPages = document.getElementById('book-pages');
    if (bookPages) bookPages.innerHTML = `${data.perspective.bookPages}<span class="big-label">pages</span>`;

    const warPeace = document.getElementById('war-peace');
    if (warPeace) warPeace.textContent = data.perspective.warPeace;

    const cvsReceipt = document.getElementById('cvs-receipt');
    if (cvsReceipt) cvsReceipt.innerHTML = `${data.perspective.cvsReceipt}<span class="big-label">m</span>`;

    const cvsNote = document.getElementById('cvs-note');
    if (cvsNote) cvsNote.textContent = data.perspective.cvsNote;

    const totalTokens = document.getElementById('total-tokens-val');
    if (totalTokens) totalTokens.textContent = data.perspective.tokens;

    const energyVal = document.getElementById('energy-val');
    if (energyVal) energyVal.innerHTML = `${data.perspective.energy}<span class="big-label">kWh</span>`;

    const energyFun = document.getElementById('energy-fun');
    if (energyFun) energyFun.textContent = data.perspective.energyFun;

    const waterVal = document.getElementById('water-val');
    if (waterVal) waterVal.innerHTML = `${data.perspective.water}<span class="big-label">liters</span>`;

    const waterFun = document.getElementById('water-fun');
    if (waterFun) waterFun.textContent = data.perspective.waterFun;

    // Nutrition label
    const nutritionServing = document.getElementById('nutrition-serving');
    if (nutritionServing) nutritionServing.textContent = data.nutrition.serving;

    const nutritionRows = document.getElementById('nutrition-rows');
    if (nutritionRows) {
      nutritionRows.innerHTML = data.nutrition.rows.map(row => `
        <div class="nutrition-row">
          <div class="nutrition-item">
            <span class="nutrition-name">${row.name}${row.sup ? `<sup>${row.sup}</sup>` : ''}</span>
            <span class="nutrition-desc">${row.desc}</span>
          </div>
          <span class="nutrition-val">${row.val}</span>
        </div>
      `).join('');
    }

    const clearAskRatio = document.getElementById('clear-ask-ratio');
    if (clearAskRatio) clearAskRatio.textContent = data.nutrition.clearAskRatio;
  }

  function getThemeColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      accent: style.getPropertyValue('--accent').trim() || '#111111',
      textMuted: style.getPropertyValue('--text-muted').trim() || '#999999',
      border: style.getPropertyValue('--border').trim() || '#e5e5e5',
      bg: style.getPropertyValue('--bg').trim() || '#ffffff',
      bgCard: style.getPropertyValue('--bg-card').trim() || '#fafafa',
      hourPeak: style.getPropertyValue('--color-hour-peak').trim() || '#06be43',
      dayPeak: style.getPropertyValue('--color-day-peak').trim() || '#cc75ff',
      monthPeak: style.getPropertyValue('--color-month-peak').trim() || '#ff6101'
    };
  }

  // Popping color palette - single source of truth
  function getPoppingColors() {
    const style = getComputedStyle(document.documentElement);
    return {
      coral: style.getPropertyValue('--color-coral').trim() || '#FF6B6B',
      amber: style.getPropertyValue('--color-amber').trim() || '#FFAB40',
      lime: style.getPropertyValue('--color-lime').trim() || '#9CCC65',
      teal: style.getPropertyValue('--color-teal').trim() || '#26C6DA',
      sky: style.getPropertyValue('--color-sky').trim() || '#42A5F5',
      violet: style.getPropertyValue('--color-violet').trim() || '#7E57C2',
      pink: style.getPropertyValue('--color-pink').trim() || '#EC407A',
      orange: style.getPropertyValue('--color-orange').trim() || '#FF7043',
    };
  }

  // Get palette as array for charts
  function getPoppingPalette() {
    const c = getPoppingColors();
    return [c.coral, c.amber, c.lime, c.teal, c.sky, c.violet, c.pink, c.orange];
  }

  // Create shared tooltip
  let tooltip = null;
  function getTooltip() {
    if (!tooltip) {
      tooltip = d3.select('body')
        .append('div')
        .attr('class', 'chart-tooltip')
        .style('position', 'absolute')
        .style('pointer-events', 'none')
        .style('opacity', 0)
        .style('background', 'var(--bg)')
        .style('border', '1px solid var(--border)')
        .style('border-radius', '6px')
        .style('padding', '6px 10px')
        .style('font-size', '12px')
        .style('font-family', 'Inter, sans-serif')
        .style('box-shadow', '0 2px 8px rgba(0,0,0,0.1)')
        .style('z-index', '1000')
        .style('white-space', 'nowrap');
    }
    return tooltip;
  }

  function showTooltip(event, text) {
    const tip = getTooltip();
    tip.html(text)
      .style('opacity', 1)
      .style('left', (event.pageX + 10) + 'px')
      .style('top', (event.pageY - 10) + 'px');
  }

  function hideTooltip() {
    const tip = getTooltip();
    tip.style('opacity', 0);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Hour Chart (vertical bars)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderHourChart(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const maxValue = Math.max(...data.values);
    const maxIndex = data.values.indexOf(maxValue);

    const labelEl = document.getElementById('hour-label');
    if (labelEl) labelEl.textContent = `By Hour, peak ${maxValue.toLocaleString()}`;

    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const barGap = 2;
    const barWidth = (width - (data.values.length - 1) * barGap) / data.values.length;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    const yScale = d3.scaleLinear()
      .domain([0, maxValue])
      .range([0, height]);

    svg.selectAll('rect')
      .data(data.values)
      .enter()
      .append('rect')
      .attr('x', (d, i) => i * (barWidth + barGap))
      .attr('y', d => height - yScale(d))
      .attr('width', barWidth)
      .attr('height', d => Math.max(2, yScale(d)))
      .attr('rx', 2)
      .attr('ry', 2)
      .attr('fill', (d, i) => i === maxIndex ? colors.hourPeak : colors.accent)
      .attr('opacity', (d, i) => i === maxIndex ? 1 : 0.2)
      .style('cursor', 'pointer')
      .on('mouseenter', function(event, d) {
        showTooltip(event, d.toLocaleString());
      })
      .on('mousemove', function(event, d) {
        showTooltip(event, d.toLocaleString());
      })
      .on('mouseleave', hideTooltip);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Day Chart (horizontal bars on desktop, vertical bars on mobile)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderDayChart(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const maxValue = Math.max(...data.values);
    const maxIndex = data.values.indexOf(maxValue);
    const isMobile = window.innerWidth <= 768;

    const labelEl = document.getElementById('day-label');
    if (labelEl) labelEl.textContent = `By Day, peak ${maxValue.toLocaleString()}`;

    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    if (isMobile) {
      // Vertical bars on mobile (like hour chart)
      const barGap = 4;
      const barWidth = (width - (data.values.length - 1) * barGap) / data.values.length;

      const yScale = d3.scaleLinear()
        .domain([0, maxValue])
        .range([0, height]);

      svg.selectAll('rect')
        .data(data.values)
        .enter()
        .append('rect')
        .attr('x', (d, i) => i * (barWidth + barGap))
        .attr('y', d => height - yScale(d))
        .attr('width', barWidth)
        .attr('height', d => Math.max(4, yScale(d)))
        .attr('rx', 2)
        .attr('ry', 2)
        .attr('fill', (d, i) => i === maxIndex ? colors.dayPeak : colors.accent)
        .attr('opacity', (d, i) => i === maxIndex ? 1 : 0.2)
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
          showTooltip(event, d.toLocaleString());
        })
        .on('mousemove', function(event, d) {
          showTooltip(event, d.toLocaleString());
        })
        .on('mouseleave', hideTooltip);
    } else {
      // Horizontal bars on desktop/tablet
      const labelWidth = 16;
      const barGap = 4;
      const barHeight = (height - (data.values.length - 1) * barGap) / data.values.length;

      const xScale = d3.scaleLinear()
        .domain([0, maxValue])
        .range([0, width - labelWidth - 8]);

      const rows = svg.selectAll('g')
        .data(data.values)
        .enter()
        .append('g')
        .attr('transform', (d, i) => `translate(0, ${i * (barHeight + barGap)})`);

      // Labels
      rows.append('text')
        .attr('x', 0)
        .attr('y', barHeight / 2)
        .attr('dy', '0.35em')
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, sans-serif')
        .attr('fill', colors.textMuted)
        .text((d, i) => data.labels[i]);

      // Bars
      rows.append('rect')
        .attr('x', labelWidth)
        .attr('y', 0)
        .attr('width', d => Math.max(4, xScale(d)))
        .attr('height', barHeight)
        .attr('rx', 2)
        .attr('ry', 2)
        .attr('fill', (d, i) => i === maxIndex ? colors.dayPeak : colors.accent)
        .attr('opacity', (d, i) => i === maxIndex ? 1 : 0.2)
        .style('cursor', 'pointer')
        .on('mouseenter', function(event, d) {
          showTooltip(event, d.toLocaleString());
        })
        .on('mousemove', function(event, d) {
          showTooltip(event, d.toLocaleString());
        })
        .on('mouseleave', hideTooltip);
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Month Chart (vertical bars with labels below)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderMonthChart(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const maxValue = Math.max(...data.values);
    const maxIndex = data.values.indexOf(maxValue);

    const labelEl = document.getElementById('month-label');
    if (labelEl) labelEl.textContent = `By Month, peak ${maxValue.toLocaleString()}`;

    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const barGap = 4;
    const barWidth = (width - (data.values.length - 1) * barGap) / data.values.length;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    const yScale = d3.scaleLinear()
      .domain([0, maxValue])
      .range([0, height]);

    svg.selectAll('rect')
      .data(data.values)
      .enter()
      .append('rect')
      .attr('x', (d, i) => i * (barWidth + barGap))
      .attr('y', d => height - yScale(d))
      .attr('width', barWidth)
      .attr('height', d => Math.max(4, yScale(d)))
      .attr('rx', 2)
      .attr('ry', 2)
      .attr('fill', (d, i) => i === maxIndex ? colors.monthPeak : colors.accent)
      .attr('opacity', (d, i) => i === maxIndex ? 1 : 0.2)
      .style('cursor', 'pointer')
      .on('mouseenter', function(event, d) {
        showTooltip(event, d.toLocaleString());
      })
      .on('mousemove', function(event, d) {
        showTooltip(event, d.toLocaleString());
      })
      .on('mouseleave', hideTooltip);

    // Render labels
    const labelsEl = document.getElementById('month-labels');
    if (labelsEl) {
      labelsEl.innerHTML = data.labels.map(l => `<span>${l}</span>`).join('');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Timeline Chart (smooth area chart with grid lines)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderTimelineChart(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const maxValue = Math.max(...data.values);
    const maxIndex = data.values.indexOf(maxValue);

    // Update label
    const labelEl = document.getElementById('timeline-label');
    if (labelEl) labelEl.textContent = `Over Time, peak ${maxValue.toLocaleString()}`;

    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const padding = { top: 10, right: 0, bottom: 24, left: 0 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    const g = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${padding.top})`);

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, data.values.length - 1])
      .range([0, chartWidth]);

    const yScale = d3.scaleLinear()
      .domain([0, maxValue])
      .range([chartHeight, 0]);

    // Find year boundaries for grid lines and labels
    const yearBoundaries = [];
    data.labels.forEach((label, i) => {
      if (label === 'Jan' && i > 0) {
        yearBoundaries.push({ index: i, year: data.years[i] });
      }
    });

    // Draw dashed vertical grid lines for each month
    data.labels.forEach((label, i) => {
      if (i === 0) return; // Skip first month
      const isYearBoundary = label === 'Jan';
      if (!isYearBoundary) {
        g.append('line')
          .attr('x1', xScale(i))
          .attr('x2', xScale(i))
          .attr('y1', 0)
          .attr('y2', chartHeight)
          .attr('stroke', colors.border)
          .attr('stroke-width', 1)
          .attr('stroke-dasharray', '4,3')
          .attr('opacity', 0.7);
      }
    });

    // Draw darker dashed vertical grid lines at year boundaries
    yearBoundaries.forEach(({ index }) => {
      g.append('line')
        .attr('x1', xScale(index))
        .attr('x2', xScale(index))
        .attr('y1', 0)
        .attr('y2', chartHeight)
        .attr('stroke', colors.accent)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.2);
    });

    // Area generator with smooth curve
    const area = d3.area()
      .x((d, i) => xScale(i))
      .y0(chartHeight)
      .y1(d => yScale(d))
      .curve(d3.curveMonotoneX);

    // Line generator
    const line = d3.line()
      .x((d, i) => xScale(i))
      .y(d => yScale(d))
      .curve(d3.curveMonotoneX);

    // Draw area
    g.append('path')
      .datum(data.values)
      .attr('d', area)
      .attr('fill', colors.accent)
      .attr('opacity', 0.1);

    // Draw line
    g.append('path')
      .datum(data.values)
      .attr('d', line)
      .attr('fill', 'none')
      .attr('stroke', colors.accent)
      .attr('stroke-width', 2)
      .attr('opacity', 0.6);

    // Highlight peak point
    const peakCircle = g.append('circle')
      .attr('cx', xScale(maxIndex))
      .attr('cy', yScale(maxValue))
      .attr('r', 4)
      .attr('fill', colors.accent);

    // Hover indicator circle (hidden by default)
    const hoverCircle = g.append('circle')
      .attr('r', 4)
      .attr('fill', colors.accent)
      .attr('opacity', 0)
      .style('pointer-events', 'none');

    // Invisible hover areas for each data point
    const barWidth = chartWidth / data.values.length;

    g.selectAll('.hover-area')
      .data(data.values)
      .enter()
      .append('rect')
      .attr('class', 'hover-area')
      .attr('x', (d, i) => xScale(i) - barWidth / 2)
      .attr('y', 0)
      .attr('width', barWidth)
      .attr('height', chartHeight)
      .attr('fill', 'transparent')
      .style('cursor', 'pointer')
      .on('mouseenter', function(event, d) {
        const i = data.values.indexOf(d);
        showTooltip(event, `${data.labels[i]}: ${d.toLocaleString()}`);
        hoverCircle
          .attr('cx', xScale(i))
          .attr('cy', yScale(d))
          .attr('opacity', i === maxIndex ? 0 : 0.8);
      })
      .on('mousemove', function(event, d) {
        const i = data.values.indexOf(d);
        showTooltip(event, `${data.labels[i]}: ${d.toLocaleString()}`);
      })
      .on('mouseleave', function() {
        hideTooltip();
        hoverCircle.attr('opacity', 0);
      });

    // X-axis labels: show years, dropping labels that would collide
    const labelsGroup = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${height - 6})`);

    // Build list of all potential labels with their x positions
    const firstYear = data.years[0];
    const allLabels = [{ x: 0, year: firstYear }];
    yearBoundaries.forEach(({ index, year }) => {
      allLabels.push({ x: xScale(index), year });
    });

    // Filter out labels that are too close (less than 40px apart)
    const minSpacing = 40;
    const visibleLabels = [];
    allLabels.forEach((label, i) => {
      if (i === 0) {
        // Always consider first label, but it might get dropped if next is too close
        visibleLabels.push(label);
      } else {
        const prevVisible = visibleLabels[visibleLabels.length - 1];
        if (label.x - prevVisible.x >= minSpacing) {
          visibleLabels.push(label);
        } else {
          // Drop the earlier label in favor of the later one (at year boundary)
          visibleLabels[visibleLabels.length - 1] = label;
        }
      }
    });

    // Render visible labels
    visibleLabels.forEach(({ x, year }, i) => {
      const anchor = x === 0 ? 'start' : (i === visibleLabels.length - 1 && x > chartWidth - 20) ? 'end' : 'middle';
      labelsGroup.append('text')
        .attr('x', x)
        .attr('y', 0)
        .attr('text-anchor', anchor)
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, sans-serif')
        .attr('fill', colors.textMuted)
        .text(year);
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Top Topics List
  // ═══════════════════════════════════════════════════════════════════════════
  function renderTopicsList(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = data.map(topic =>
      `<div class="topic"><span class="topic-rank">${topic.rank}</span><span class="topic-name">${topic.name}</span><span class="topic-pct">${topic.pct}%</span></div>`
    ).join('');
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Streamgraph (Topic Time Machine)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderStreamgraph(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height || 200;
    const padding = { top: 10, right: 0, bottom: 24, left: 0 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    const g = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${padding.top})`);

    // Generate a vibrant color palette using shared popping colors
    const baseColors = getPoppingPalette();
    const numKeys = data.keys.length;
    const colorPalette = data.keys.map((_, i) => baseColors[i % baseColors.length]);

    const color = d3.scaleOrdinal()
      .domain(data.keys)
      .range(colorPalette);

    // Stack generator with wiggle offset for streamgraph
    const stack = d3.stack()
      .keys(data.keys)
      .offset(d3.stackOffsetWiggle)
      .order(d3.stackOrderInsideOut);

    const series = stack(data.values);

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, data.values.length - 1])
      .range([0, chartWidth]);

    const yMin = d3.min(series, layer => d3.min(layer, d => d[0]));
    const yMax = d3.max(series, layer => d3.max(layer, d => d[1]));

    const yScale = d3.scaleLinear()
      .domain([yMin, yMax])
      .range([chartHeight, 0]);

    // Find year boundaries for grid lines
    const yearBoundaries = [];
    let prevYear = null;
    data.values.forEach((d, i) => {
      const year = d.period.split('-')[0];
      if (year !== prevYear) {
        if (prevYear !== null) {
          yearBoundaries.push(i);
        }
        prevYear = year;
      }
    });

    // Draw dashed vertical grid lines at year boundaries
    yearBoundaries.forEach(index => {
      g.append('line')
        .attr('x1', xScale(index))
        .attr('x2', xScale(index))
        .attr('y1', 0)
        .attr('y2', chartHeight)
        .attr('stroke', colors.accent)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.2);
    });

    // Area generator
    const area = d3.area()
      .x((d, i) => xScale(i))
      .y0(d => yScale(d[0]))
      .y1(d => yScale(d[1]))
      .curve(d3.curveBasis);

    // Draw streams
    g.selectAll('path')
      .data(series)
      .enter()
      .append('path')
      .attr('d', area)
      .attr('fill', d => color(d.key))
      .attr('opacity', 0.85)
      .style('cursor', 'pointer')
      .on('mouseenter', function(event, d) {
        // Dim other streams
        g.selectAll('path').attr('opacity', 0.3);
        d3.select(this).attr('opacity', 1);
        showTooltip(event, d.key);
      })
      .on('mousemove', function(event, d) {
        showTooltip(event, d.key);
      })
      .on('mouseleave', function() {
        g.selectAll('path').attr('opacity', 0.85);
        hideTooltip();
      });

    // Year labels on x-axis
    const labelsGroup = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${height - 6})`);

    // Find year boundaries
    const yearLabels = [];
    let lastYear = null;
    data.values.forEach((d, i) => {
      const year = d.period.split('-')[0];
      if (year !== lastYear) {
        yearLabels.push({ index: i, year });
        lastYear = year;
      }
    });

    yearLabels.forEach(({ index, year }, i) => {
      const x = xScale(index);
      const anchor = index === 0 ? 'start' : 'middle';

      // Create a group for each label (rect + text together)
      const labelGroup = labelsGroup.append('g');

      // Add text first to measure it
      const textNode = labelGroup.append('text')
        .attr('x', x)
        .attr('y', 0)
        .attr('text-anchor', anchor)
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, sans-serif')
        .attr('fill', colors.textMuted)
        .text(year);

      // Get text dimensions and insert background rect before text
      const bbox = textNode.node().getBBox();
      labelGroup.insert('rect', 'text')
        .attr('x', bbox.x - 4)
        .attr('y', bbox.y - 1)
        .attr('width', bbox.width + 8)
        .attr('height', bbox.height + 2)
        .attr('fill', colors.bgCard);
    });

    // Render legend
    const legendEl = document.getElementById('streamgraph-legend');
    if (legendEl) {
      legendEl.innerHTML = data.keys.map((key, i) =>
        `<span class="legend-item"><span class="legend-color" style="background:${colorPalette[i]}"></span>${key}</span>`
      ).join('');
    }
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Frustration Chart (Butterfly/Mirror Chart)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderFrustrationChart(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    const colors = getThemeColors();
    const popping = getPoppingColors();
    const frustrationColor = popping.coral;
    const apologyColor = popping.teal;

    const rect = containerEl.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height || 200;
    const padding = { top: 10, right: 10, bottom: 24, left: 10 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('display', 'block');

    const g = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${padding.top})`);

    // Scales
    const xScale = d3.scaleLinear()
      .domain([0, data.timeline.swears.length - 1])
      .range([0, chartWidth]);

    const maxSwear = Math.max(...data.timeline.swears);
    const maxApology = Math.max(...data.timeline.apologies);

    const yScale = d3.scaleLinear()
      .domain([-maxSwear * 1.1, maxApology * 1.1])
      .range([chartHeight, 0]);

    // Find year boundaries for grid lines
    const yearBoundaries = [];
    let prevLabel = null;
    data.timeline.labels.forEach((label, i) => {
      const year = label.split(' ')[1];
      const prevYear = prevLabel ? prevLabel.split(' ')[1] : null;
      if (year !== prevYear && prevYear !== null) {
        yearBoundaries.push({ index: i, year });
      }
      prevLabel = label;
    });

    // Draw year boundary lines
    yearBoundaries.forEach(({ index }) => {
      g.append('line')
        .attr('x1', xScale(index))
        .attr('x2', xScale(index))
        .attr('y1', 0)
        .attr('y2', chartHeight)
        .attr('stroke', colors.accent)
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '4,3')
        .attr('opacity', 0.2);
    });

    // Draw center line (y=0)
    g.append('line')
      .attr('x1', 0)
      .attr('x2', chartWidth)
      .attr('y1', yScale(0))
      .attr('y2', yScale(0))
      .attr('stroke', colors.border)
      .attr('stroke-width', 1);

    // Area generators
    const areaSwear = d3.area()
      .x((d, i) => xScale(i))
      .y0(yScale(0))
      .y1((d) => yScale(-d))
      .curve(d3.curveMonotoneX);

    const areaApology = d3.area()
      .x((d, i) => xScale(i))
      .y0(yScale(0))
      .y1((d) => yScale(d))
      .curve(d3.curveMonotoneX);

    // Line generators
    const lineSwear = d3.line()
      .x((d, i) => xScale(i))
      .y((d) => yScale(-d))
      .curve(d3.curveMonotoneX);

    const lineApology = d3.line()
      .x((d, i) => xScale(i))
      .y((d) => yScale(d))
      .curve(d3.curveMonotoneX);

    // Draw swear area (below center)
    g.append('path')
      .datum(data.timeline.swears)
      .attr('d', areaSwear)
      .attr('fill', frustrationColor)
      .attr('opacity', 0.3);

    // Draw swear line
    g.append('path')
      .datum(data.timeline.swears)
      .attr('d', lineSwear)
      .attr('fill', 'none')
      .attr('stroke', frustrationColor)
      .attr('stroke-width', 2);

    // Draw apology area (above center)
    g.append('path')
      .datum(data.timeline.apologies)
      .attr('d', areaApology)
      .attr('fill', apologyColor)
      .attr('opacity', 0.3);

    // Draw apology line
    g.append('path')
      .datum(data.timeline.apologies)
      .attr('d', lineApology)
      .attr('fill', 'none')
      .attr('stroke', apologyColor)
      .attr('stroke-width', 2);

    // Hover line (hidden by default)
    const hoverLine = g.append('line')
      .attr('class', 'hover-line')
      .attr('y1', 0)
      .attr('y2', chartHeight)
      .attr('stroke', colors.textMuted)
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0);

    // Hover areas for tooltips
    const barWidth = chartWidth / data.timeline.swears.length;

    g.selectAll('.hover-area')
      .data(data.timeline.swears.map((d, i) => ({ swears: d, apologies: data.timeline.apologies[i], index: i })))
      .enter()
      .append('rect')
      .attr('class', 'hover-area')
      .attr('x', (d) => xScale(d.index) - barWidth / 2)
      .attr('y', 0)
      .attr('width', barWidth)
      .attr('height', chartHeight)
      .attr('fill', 'transparent')
      .style('cursor', 'pointer')
      .on('mouseenter', function(event, d) {
        showTooltip(event, `Frustration: ${d.swears}<br>Apologies: ${d.apologies}`);
        hoverLine
          .attr('x1', xScale(d.index))
          .attr('x2', xScale(d.index))
          .attr('opacity', 0.5);
      })
      .on('mousemove', function(event, d) {
        showTooltip(event, `Frustration: ${d.swears}<br>Apologies: ${d.apologies}`);
        hoverLine
          .attr('x1', xScale(d.index))
          .attr('x2', xScale(d.index))
          .attr('opacity', 0.5);
      })
      .on('mouseleave', function() {
        hideTooltip();
        hoverLine.attr('opacity', 0);
      });

    // Year labels
    const labelsGroup = svg.append('g')
      .attr('transform', `translate(${padding.left}, ${height - 6})`);

    // Build year labels
    const yearLabels = [];
    let lastYear = null;
    data.timeline.labels.forEach((label, i) => {
      const year = label.split(' ')[1];
      if (year !== lastYear) {
        yearLabels.push({ index: i, year });
        lastYear = year;
      }
    });

    yearLabels.forEach(({ index, year }, i) => {
      const x = xScale(index);
      const anchor = index === 0 ? 'start' : 'middle';

      // Create a group for each label (rect + text together)
      const labelGroup = labelsGroup.append('g');

      // Add text first to measure it
      const textNode = labelGroup.append('text')
        .attr('x', x)
        .attr('y', 0)
        .attr('text-anchor', anchor)
        .attr('font-size', '10px')
        .attr('font-family', 'Inter, sans-serif')
        .attr('fill', colors.textMuted)
        .text(year);

      // Get text dimensions and insert background rect before text
      const bbox = textNode.node().getBBox();
      labelGroup.insert('rect', 'text')
        .attr('x', bbox.x - 4)
        .attr('y', bbox.y - 1)
        .attr('width', bbox.width + 8)
        .attr('height', bbox.height + 2)
        .attr('fill', colors.bgCard);
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Word Cloud Scaling Helper
  // ═══════════════════════════════════════════════════════════════════════════
  function setupWordCloudCanvas(canvas, containerWidth, containerHeight) {
    const dpr = window.devicePixelRatio || 1;
    const isMobile = window.innerWidth <= 768;

    // Set canvas size accounting for device pixel ratio
    canvas.width = containerWidth * dpr;
    canvas.height = containerHeight * dpr;
    canvas.style.width = containerWidth + 'px';
    canvas.style.height = containerHeight + 'px';

    // Calculate ellipticity based on container aspect ratio
    // value < 1 = WIDER ellipse, value > 1 = TALLER ellipse
    const aspectRatio = containerWidth / containerHeight;
    const ellipticity = Math.max(0.3, Math.min(3, 1 / aspectRatio));

    return { dpr, isMobile, ellipticity };
  }

  function calculateWordCloudScale(canvas, wordSizes, isMobile, dpr) {
    // Calculate area needed vs available
    const canvasArea = canvas.width * canvas.height;
    const estimatedWordArea = wordSizes.reduce((sum, size) => sum + size * size * 0.8, 0);
    const baseScale = Math.sqrt(canvasArea / estimatedWordArea);

    // Scale factor accounts for dpr (canvas pixels vs CSS pixels)
    const dprFactor = 1;
    return (isMobile ? baseScale * 1.3 : baseScale * 0.85) * dprFactor;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Frustration Word Cloud
  // ═══════════════════════════════════════════════════════════════════════════
  function renderFrustrationCloud(data) {
    const container = document.getElementById('frustration-cloud');
    if (!container || typeof WordCloud === 'undefined') return;

    // Clear previous content
    container.innerHTML = '';

    const card = container.parentElement;
    const rect = card.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;

    // Set container size to fill the entire card
    container.style.width = width + 'px';
    container.style.height = height + 'px';
    container.style.position = 'absolute';
    container.style.top = '0';
    container.style.left = '0';

    const isMobile = window.innerWidth <= 768;

    // Normalize counts to font sizes (minSize to maxSize range)
    const counts = data.wordcloud.map(w => w.count);
    const maxCount = Math.max(...counts);
    const minCount = Math.min(...counts);

    // Larger font sizes to fill more space
    const minFontSize = isMobile ? 12 : 14;
    const maxFontSize = isMobile ? 80 : 100;

    const wordList = data.wordcloud.map(item => {
      // Log scale for better distribution
      const logCount = Math.log(item.count + 1);
      const logMax = Math.log(maxCount + 1);
      const logMin = Math.log(minCount + 1);
      const normalized = (logCount - logMin) / (logMax - logMin);
      const fontSize = minFontSize + normalized * (maxFontSize - minFontSize);
      return [item.word, fontSize];
    });

    // Popping color palette for frustration words (using shared palette)
    const aggressiveColors = getPoppingPalette();

    const fontClasses = ['wc-serif', 'wc-sans', 'wc-mono', 'wc-display'];

    // Calculate weight factor to fill the space
    const area = width * height;
    const wordArea = wordList.reduce((sum, [, size]) => sum + size * size * 0.5, 0);
    const weightFactor = Math.sqrt(area / wordArea) * 0.7;

    WordCloud(container, {
      list: wordList.map(([word, size]) => [word, size * weightFactor]),
      fontFamily: 'Inter, sans-serif',
      classes: function(word, weight, fontSize, extraDataArray) {
        const cls = fontClasses[Math.floor(Math.random() * fontClasses.length)];
        return cls;
      },
      color: function() {
        return aggressiveColors[Math.floor(Math.random() * aggressiveColors.length)];
      },
      rotateRatio: 0.5,  // 50% chance of rotation
      rotationSteps: 2,  // Only 0° or 90°
      backgroundColor: 'transparent',
      drawOutOfBound: false,
      shrinkToFit: false,
      gridSize: 4,
      shuffle: true,
      minSize: 0,
      shape: 'square',
      ellipticity: 1
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Emoji Word Cloud (Combined)
  // ═══════════════════════════════════════════════════════════════════════════
  function renderEmojiClouds(data) {
    // Update label with combined counts
    const emojiLabel = document.getElementById('emoji-label');
    if (emojiLabel) {
      emojiLabel.textContent = `You sent ${data.user.total.toLocaleString()} emojis, ChatGPT sent ${data.assistant.total.toLocaleString()}`;
    }

    // Merge both emoji sets, combining counts for duplicates
    const emojiMap = new Map();

    data.user.emojis.forEach(([emoji, count]) => {
      emojiMap.set(emoji, (emojiMap.get(emoji) || 0) + count);
    });

    data.assistant.emojis.forEach(([emoji, count]) => {
      emojiMap.set(emoji, (emojiMap.get(emoji) || 0) + count);
    });

    // Convert to array and sort by count descending
    const combinedEmojis = Array.from(emojiMap.entries())
      .sort((a, b) => b[1] - a[1]);

    // Render combined cloud
    const canvas = document.getElementById('emoji-cloud');
    if (!canvas || typeof WordCloud === 'undefined') return;

    // Get the wrapper dimensions (positioned absolutely in card)
    const wrapper = canvas.parentElement;
    const rect = wrapper.getBoundingClientRect();
    const isMobileCheck = window.innerWidth <= 768;

    // Use wrapper dimensions (which fills the card)
    const width = rect.width;
    const height = rect.height;

    const { dpr, isMobile, ellipticity } = setupWordCloudCanvas(canvas, width, height);

    // Use log scale for better size distribution
    const minFontSize = isMobile ? 24 : 16;
    const maxFontSize = isMobile ? 160 : 72;
    const counts = combinedEmojis.map(e => e[1]);
    const maxCount = Math.max(...counts);
    const minCount = Math.min(...counts);

    const normalizedEmojis = combinedEmojis.map(([emoji, count]) => {
      // Log scale for better distribution
      const logCount = Math.log(count + 1);
      const logMax = Math.log(maxCount + 1);
      const logMin = Math.log(minCount + 1);
      const normalized = (logCount - logMin) / (logMax - logMin);
      const size = minFontSize + normalized * (maxFontSize - minFontSize);
      return [emoji, size];
    });

    const scaleFactor = calculateWordCloudScale(canvas, normalizedEmojis.map(e => e[1]), isMobile, dpr);

    WordCloud(canvas, {
      list: normalizedEmojis.map(([emoji, size]) => [emoji, size * scaleFactor]),
      fontFamily: 'Apple Color Emoji, Segoe UI Emoji, Noto Color Emoji, sans-serif',
      rotateRatio: 0,
      backgroundColor: 'transparent',
      drawOutOfBound: false,
      shrinkToFit: true,
      gridSize: Math.max(2, 4 * dpr),
      shuffle: true,
      weightFactor: 1,
      minSize: 0,
      shape: 'square'
    });
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Tarot Card Renderer
  // ═══════════════════════════════════════════════════════════════════════════
  function renderTarot(container, data) {
    const containerEl = document.querySelector(container);
    if (!containerEl) return;

    containerEl.innerHTML = '';

    // Add overlay label
    const label = document.createElement('h2');
    label.className = 'card-label';
    label.id = 'tarot-label';
    label.textContent = `Your Tarot Card: ${data.title}`;
    containerEl.appendChild(label);

    const img = document.createElement('img');
    img.src = data.image;
    img.alt = `${data.title}: ${data.subtitle}`;
    img.className = 'tarot-image';
    containerEl.appendChild(img);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Global data store (populated after fetch)
  // ═══════════════════════════════════════════════════════════════════════════
  let appData = null;

  // ═══════════════════════════════════════════════════════════════════════════
  // Main Render Function
  // ═══════════════════════════════════════════════════════════════════════════
  function render() {
    if (!appData) return;

    renderStaticContent(appData.static);
    renderHourChart('#hour-chart', appData.charts.hourly);
    renderDayChart('#day-chart', appData.charts.daily);
    renderMonthChart('#month-chart', appData.charts.monthly);
    renderTimelineChart('#timeline-chart', appData.charts.timeline);
    renderTopicsList('#topic-list', appData.topics);
    renderStreamgraph('#streamgraph-chart', appData.streamgraph);
    renderFrustrationChart('#frustration-chart', appData.frustration);
    renderTarot('#tarot-container', appData.tarot);

    // Delay word cloud renders to ensure layout is complete
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        renderFrustrationCloud(appData.frustration);
      });
    });

    // Delay emoji cloud render to ensure layout is complete
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        renderEmojiClouds(appData.emojis);
      });
    });
  }

  let resizeTimeout;
  function handleResize() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(render, 200);
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // Initialize: Fetch data and render
  // ═══════════════════════════════════════════════════════════════════════════
  function init() {
    fetch('data.json')
      .then(response => {
        if (!response.ok) {
          throw new Error(`Failed to load data.json: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        appData = data;
        // Wait for fonts to load before rendering
        if (document.fonts && document.fonts.ready) {
          document.fonts.ready.then(render);
        } else {
          render();
        }
      })
      .catch(error => {
        console.error('Error loading data:', error);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.addEventListener('resize', handleResize);

  // Watch for theme changes
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.attributeName === 'data-theme') {
        render();
      }
    });
  });
  observer.observe(document.documentElement, { attributes: true });

})();
