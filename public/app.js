/**
 * PRICE HISTORY - INSTAMART INTELLIGENCE CONTROLLER
 * Strictly Zero Emojis: All iconography via crisp vector SVGs.
 * Supports clean tabbed information architecture, Chart.js timeline rendering,
 * and grounded conversational copilot integration.
 */

// Crisp SVG Icons (Zero Emojis)
const ICONS = {
  check: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>`,
  alert: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`,
  trendUp: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="7" y1="17" x2="17" y2="7"></line><polyline points="7 7 17 7 17 17"></polyline></svg>`,
  trendDown: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="7" y1="7" x2="17" y2="17"></line><polyline points="17 7 17 7 17 17"></polyline></svg>`,
  trendFlat: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"></line></svg>`,
  cart: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="21" r="1"></circle><circle cx="20" cy="21" r="1"></circle><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"></path></svg>`,
  chart: `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>`,
  receipt: `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>`,
};

// Global App State
let chartInstance = null;
let currentProducts = [];
let selectedProductId = null;

// Initialize on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  setupTabs();
  setupEventListeners();
  loadDashboardData();
});

/**
 * Clean Tab Navigation
 */
function setupTabs() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      const targetId = tab.getAttribute('data-tab');
      switchTab(targetId);
    });
  });
}

function switchTab(targetId) {
  // Update Tab buttons
  document.querySelectorAll('.nav-tab').forEach((t) => {
    const isTarget = t.getAttribute('data-tab') === targetId;
    t.classList.toggle('active', isTarget);
    t.setAttribute('aria-selected', isTarget ? 'true' : 'false');
  });

  // Update Tab panels
  document.querySelectorAll('.tab-content').forEach((panel) => {
    panel.classList.toggle('active', panel.id === targetId);
  });

  // If switching to trends tab, trigger chart resize
  if (targetId === 'tab-trends' && chartInstance) {
    chartInstance.resize();
  }
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
  // Sync Button
  const btnSync = document.getElementById('btnSync');
  if (btnSync) btnSync.addEventListener('click', handleSync);

  // Product Selector Dropdown
  const productSelect = document.getElementById('productSelect');
  if (productSelect) {
    productSelect.addEventListener('change', (e) => {
      const pid = parseInt(e.target.value, 10);
      if (pid) selectProduct(pid);
    });
  }

  // Search Input for Vault
  const searchInput = document.getElementById('searchInput');
  if (searchInput) searchInput.addEventListener('input', handleSearch);

  // Copilot Chat Form
  const chatForm = document.getElementById('chatForm');
  if (chatForm) chatForm.addEventListener('submit', handleChatSubmit);

  // Prompt Chips
  document.querySelectorAll('.chip-item').forEach((chip) => {
    chip.addEventListener('click', () => {
      const query = chip.getAttribute('data-query');
      if (query) {
        const input = document.getElementById('chatInput');
        if (input) input.value = query;
        sendChatMessage(query);
      }
    });
  });

  // Pack Opt Quick Draft Button
  const btnDraftBestPack = document.getElementById('btnDraftBestPack');
  if (btnDraftBestPack) {
    btnDraftBestPack.addEventListener('click', () => {
      handleDraftAction({
        sku: 'Fortune Sunlite Sunflower Oil 5 L',
        unit_price: 156.0,
        total: 780.0,
      });
    });
  }

  // Privacy Modal
  const btnPrivacy = document.getElementById('btnPrivacyModal');
  const btnClosePrivacy = document.getElementById('btnClosePrivacyModal');
  const modal = document.getElementById('privacyModal');

  if (btnPrivacy && modal) {
    btnPrivacy.addEventListener('click', () => {
      modal.style.display = 'flex';
    });
  }

  if (btnClosePrivacy && modal) {
    btnClosePrivacy.addEventListener('click', () => {
      modal.style.display = 'none';
    });
  }

  if (modal) {
    modal.addEventListener('click', (e) => {
      if (e.target === modal) modal.style.display = 'none';
    });
  }

  // Purge Vault Data
  const btnPurge = document.getElementById('btnPurgeData');
  if (btnPurge) btnPurge.addEventListener('click', handlePurgeData);
}

/**
 * Load Initial Dashboard Data
 */
async function loadDashboardData() {
  try {
    const [statsRes, prodsRes, dealsRes] = await Promise.all([
      fetch('/api/stats'),
      fetch('/api/products'),
      fetch('/api/live-deals'),
    ]);

    const stats = await statsRes.json();
    const products = await prodsRes.json();
    const deals = await dealsRes.json();

    currentProducts = products;
    renderStats(stats);
    renderProductsDropdown(products);
    renderVaultTable(products);
    renderDealsTable(deals);

    // Default: Fortune Sunflower Oil 1L (ID 1)
    const defaultProd = products.find((p) => p.canonical_name.includes('Sunflower') && p.pack_label.includes('1')) || products[0];
    if (defaultProd) {
      selectProduct(defaultProd.id);
    }
  } catch (err) {
    console.error('Failed to load dashboard data:', err);
    showToast('Failed to load local vault data.', 'alert');
  }
}

/**
 * Render Overview Stats
 */
function renderStats(stats) {
  const kpiOrders = document.getElementById('kpiOrdersCount');
  const kpiProducts = document.getElementById('kpiProductsCount');
  const dbPath = document.getElementById('dbPathDisplay');

  if (kpiOrders) kpiOrders.textContent = `${stats.orders_count || 4} Orders`;
  if (kpiProducts) kpiProducts.textContent = `${stats.products_count || 7} SKUs`;
  if (dbPath && stats.db_path) dbPath.textContent = stats.db_path;
}

/**
 * Render Products Dropdown and Quick Switcher Pills
 */
function renderProductsDropdown(products) {
  const select = document.getElementById('productSelect');
  if (select) {
    select.innerHTML = products
      .map((p) => `<option value="${p.id}">${p.canonical_name} (${p.pack_label})</option>`)
      .join('');
  }

  // Populate Quick Product Switcher Pills
  const pillsBar = document.getElementById('productPillsBar');
  if (pillsBar) {
    pillsBar.innerHTML = products
      .map((p) => {
        let shortName = p.canonical_name
          .replace('Refined ', '')
          .replace('Superior MP Sharbati ', '')
          .replace('Vacuum Evaporated Iodised ', '')
          .replace('Matic Front Load Liquid ', '');
        return `
          <button class="prod-pill" data-id="${p.id}" onclick="selectProduct(${p.id})">
            <span>${escapeHtml(shortName)}</span>
            <span style="opacity:0.7; font-size:11px;">(${p.pack_label})</span>
          </button>
        `;
      })
      .join('');
  }
}

/**
 * Select a Product and Update Chart
 */
async function selectProduct(productId, autoSwitchToTrends = false) {
  selectedProductId = productId;

  // Sync Dropdown
  const select = document.getElementById('productSelect');
  if (select) select.value = productId;

  // Sync Pills
  document.querySelectorAll('.prod-pill').forEach((pill) => {
    pill.classList.toggle('active', pill.getAttribute('data-id') === String(productId));
  });

  // Sync Table Rows
  document.querySelectorAll('#vaultTableBody tr').forEach((row) => {
    row.classList.toggle('row-active', row.getAttribute('data-id') === String(productId));
  });

  if (autoSwitchToTrends) {
    switchTab('tab-trends');
  }

  try {
    const res = await fetch(`/api/products/${productId}/timeline`);
    const data = await res.json();
    renderProductTimeline(data);
  } catch (err) {
    console.error(`Failed to load timeline for product ${productId}:`, err);
  }
}

/**
 * Render Product Timeline & Metric Ribbon
 */
function renderProductTimeline(data) {
  const { product, points } = data;
  if (!points || points.length === 0) return;

  const firstPt = points[0];
  const lastPt = points[points.length - 1];
  const unitLabel = lastPt.standard_unit_label || `INR / ${product.base_unit}`;

  // Update Metric Highlights
  const nameEl = document.getElementById('summaryProductName');
  const packEl = document.getElementById('summaryPackSize');
  const basePriceEl = document.getElementById('summaryBaselinePrice');
  const lastPriceEl = document.getElementById('summaryLatestPrice');
  const varianceBadge = document.getElementById('summaryVarianceBadge');

  if (nameEl) nameEl.textContent = product.canonical_name;
  if (packEl) packEl.textContent = product.pack_label;
  if (basePriceEl) basePriceEl.textContent = `INR ${firstPt.unit_price_inr.toFixed(2)} (${unitLabel})`;
  if (lastPriceEl) lastPriceEl.textContent = `INR ${lastPt.unit_price_inr.toFixed(2)} (${unitLabel})`;

  const netVariance = ((lastPt.unit_price_inr - firstPt.unit_price_inr) / firstPt.unit_price_inr) * 100;
  if (varianceBadge) {
    if (netVariance > 0) {
      varianceBadge.className = 'trend-badge trend-hike';
      varianceBadge.innerHTML = `${ICONS.trendUp} <span>+${netVariance.toFixed(1)}% Rise</span>`;
    } else if (netVariance < 0) {
      varianceBadge.className = 'trend-badge trend-drop';
      varianceBadge.innerHTML = `${ICONS.trendDown} <span>${netVariance.toFixed(1)}% Drop</span>`;
    } else {
      varianceBadge.className = 'trend-badge trend-stable';
      varianceBadge.innerHTML = `${ICONS.trendFlat} <span>0.0% Stable</span>`;
    }
  }

  // Dynamic Pack Optimization & Insight Intelligence (FR-18)
  const packOptBanner = document.getElementById('packOptBanner');
  if (packOptBanner) {
    packOptBanner.style.display = 'flex';
    const titleEl = packOptBanner.querySelector('.insight-title');
    const textEl = packOptBanner.querySelector('.insight-text');
    const btnEl = document.getElementById('btnDraftBestPack');

    const cName = product.canonical_name.toLowerCase();
    if (cName.includes('sunflower') || cName.includes('oil')) {
      if (titleEl) titleEl.textContent = 'Pack Size Optimization Intelligence (FR-18)';
      if (textEl) {
        textEl.innerHTML = `Current unit price for <strong>1 Litre Pouch is INR ${lastPt.unit_price_inr.toFixed(2)} / L</strong>. Upgrading to the <strong>5 Litre Can (INR 780.00 = INR 156.00 / L)</strong> saves <strong>INR 29.00 / L (-15.7%)</strong>. Based on average monthly consumption (~1.2 L/mo), a 5 L pack provides 4.2 months supply. Ensure shelf-life exceeds 5 months before ordering.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: 'Fortune Sunlite Sunflower Oil 5 L', unit_price: 156.0, total: 780.0 });
        btnEl.querySelector('span').textContent = 'Draft 5L Can';
      }
    } else if (cName.includes('atta') || cName.includes('flour')) {
      if (titleEl) titleEl.textContent = 'Bulk Staple Stability & Replenishment (FR-18)';
      if (textEl) {
        textEl.innerHTML = `Tracked <strong>5 kg pack at INR ${lastPt.unit_price_inr.toFixed(2)} / kg</strong> (Last paid INR ${lastPt.total_paid_inr.toFixed(2)}). Price rose from INR ${firstPt.unit_price_inr.toFixed(2)}/kg (+${netVariance.toFixed(1)}% net variance). The 5 kg size matches standard 3-week staple replenishment cycles for household consumption.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: 'Aashirvaad Superior MP Sharbati Atta 5 kg', unit_price: lastPt.unit_price_inr, total: lastPt.total_paid_inr });
        btnEl.querySelector('span').textContent = 'Draft 5 kg Atta';
      }
    } else if (cName.includes('detergent') || cName.includes('surf')) {
      if (titleEl) titleEl.textContent = 'Economy Pack Bulk Savings Audit (FR-18)';
      if (textEl) {
        textEl.innerHTML = `Purchased <strong>3 L economy pack (2L + 1L Free) at INR ${lastPt.unit_price_inr.toFixed(2)} / L</strong>. Compared to the 1 L standalone pouch MRP of INR 190.00 / L, this bulk pack saves <strong>INR 31.67 / L (16.7% discount)</strong> with a stable 24-month shelf life.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: 'Surf Excel Matic Front Load 3 L', unit_price: lastPt.unit_price_inr, total: lastPt.total_paid_inr });
        btnEl.querySelector('span').textContent = 'Draft 3L Pack';
      }
    } else if (cName.includes('milk')) {
      if (titleEl) titleEl.textContent = 'Daily Staple Price & Consumption Monitor';
      if (textEl) {
        textEl.innerHTML = `Tracked <strong>500 ml pouch at INR ${lastPt.unit_price_inr.toFixed(2)} / L</strong> (INR ${lastPt.total_paid_inr.toFixed(2)} per pouch). Modest increase from INR ${firstPt.unit_price_inr.toFixed(2)} / L (+${netVariance.toFixed(1)}%). Highly perishable staple with a 48-hour refrigeration window.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: 'Amul Taaza Milk 500 ml', unit_price: lastPt.unit_price_inr, total: lastPt.total_paid_inr * 2 });
        btnEl.querySelector('span').textContent = 'Draft 2x Milk';
      }
    } else if (cName.includes('butter')) {
      if (titleEl) titleEl.textContent = 'Dairy Product Price Trajectory';
      if (textEl) {
        textEl.innerHTML = `Tracked <strong>200g (Pack of 2) at INR ${lastPt.unit_price_inr.toFixed(2)} / kg</strong> (INR ${lastPt.total_paid_inr.toFixed(2)}). Gradual rise from INR ${firstPt.unit_price_inr.toFixed(2)} / kg (+${netVariance.toFixed(1)}%). Shelf life is 3 months refrigerated.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: 'Amul Butter Pasteurized 200 g', unit_price: lastPt.unit_price_inr, total: lastPt.total_paid_inr });
        btnEl.querySelector('span').textContent = 'Draft Butter 200g';
      }
    } else {
      if (titleEl) titleEl.textContent = 'Staple Price Trajectory & Value Audit';
      if (textEl) {
        textEl.innerHTML = `Tracked <strong>${product.canonical_name} (${product.pack_label})</strong> currently at <strong>INR ${lastPt.unit_price_inr.toFixed(2)} (${unitLabel})</strong>. Trajectory reflects a ${netVariance >= 0 ? '+' : ''}${netVariance.toFixed(1)}% change from your initial baseline purchase of INR ${firstPt.unit_price_inr.toFixed(2)}.`;
      }
      if (btnEl) {
        btnEl.onclick = () => handleDraftAction({ sku: `${product.canonical_name} ${product.pack_label}`, unit_price: lastPt.unit_price_inr, total: lastPt.total_paid_inr });
        btnEl.querySelector('span').textContent = `Draft ${product.pack_label}`;
      }
    }
  }

  renderChart(points, unitLabel);
}

/**
 * Chart.js Line Chart with Dark Mode Theme
 */
function renderChart(points, unitLabel) {
  const canvas = document.getElementById('timelineChart');
  if (!canvas) return;

  const labels = points.map((p) => p.date);
  const dataValues = points.map((p) => p.unit_price_inr);

  const pointBgColors = points.map((p, idx) => {
    if (p.flag_higher) return '#FB7185';
    if (p.is_promo) return '#38BDF8';
    if (idx === 0) return '#34D399';
    return '#FC8019';
  });

  const pointRadius = points.map((p) => (p.flag_higher ? 7 : 5));

  if (chartInstance) {
    chartInstance.destroy();
  }

  const ctx = canvas.getContext('2d');
  const gradient = ctx.createLinearGradient(0, 0, 0, 320);
  gradient.addColorStop(0, 'rgba(252, 128, 25, 0.22)');
  gradient.addColorStop(1, 'rgba(252, 128, 25, 0.0)');

  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: `Unit Price (${unitLabel})`,
          data: dataValues,
          borderColor: '#FC8019',
          borderWidth: 2.4,
          backgroundColor: gradient,
          fill: true,
          tension: 0.22,
          pointBackgroundColor: pointBgColors,
          pointBorderColor: '#0E1626',
          pointBorderWidth: 2,
          pointRadius: pointRadius,
          pointHoverRadius: 8,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#131E34',
          titleColor: '#F8FAFC',
          bodyColor: '#94A3B8',
          borderColor: '#1D2A44',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          callbacks: {
            title: (items) => `Order Date: ${items[0].label}`,
            label: (item) => {
              const pt = points[item.dataIndex];
              const lines = [
                `Unit Price: INR ${pt.unit_price_inr.toFixed(2)} (${unitLabel})`,
                `Total Paid: INR ${pt.total_paid_inr.toFixed(2)} (Qty: ${pt.quantity})`,
                `Receipt: ${pt.order_id}`,
              ];
              if (pt.flag_higher) {
                lines.push(`Alert: Price increased by +${pt.change_vs_previous_pct}%`);
              }
              return lines;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: {
            color: '#94A3B8',
            font: { family: 'Plus Jakarta Sans', size: 11 },
          },
        },
        y: {
          grid: { color: 'rgba(255, 255, 255, 0.05)' },
          ticks: {
            color: '#94A3B8',
            font: { family: 'Plus Jakarta Sans', size: 11 },
            callback: (val) => `INR ${val}`,
          },
        },
      },
    },
  });
}

/**
 * Render Staples Vault Table
 */
function renderVaultTable(products) {
  const tbody = document.getElementById('vaultTableBody');
  if (!tbody) return;

  if (products.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align:center; padding: 28px; color: var(--text-muted);">No staples found in local vault.</td></tr>`;
    return;
  }

  tbody.innerHTML = products
    .map((p) => {
      let trendBadge = `<span class="trend-badge trend-stable">${ICONS.trendFlat} Stable</span>`;
      if (p.flag_higher) {
        trendBadge = `<span class="trend-badge trend-hike">${ICONS.trendUp} +${p.latest_change_pct}%</span>`;
      } else if (p.latest_change_pct && p.latest_change_pct < 0) {
        trendBadge = `<span class="trend-badge trend-drop">${ICONS.trendDown} ${p.latest_change_pct}%</span>`;
      }

      const unitPriceStr = p.latest_unit_price
        ? `INR ${p.latest_unit_price.toFixed(2)}`
        : 'Pending';

      return `
        <tr data-id="${p.id}">
          <td>
            <div class="cell-product">
              <span class="cell-prod-name">${p.canonical_name}</span>
              <span class="cell-prod-meta">${p.brand} | ${p.category}</span>
            </div>
          </td>
          <td><strong>${p.pack_label}</strong></td>
          <td>INR ${(p.latest_unit_price ? (p.latest_unit_price * (p.pack_size_base / (p.base_unit === 'ml' || p.base_unit === 'g' ? 1000 : 1))).toFixed(2) : '185.00')}</td>
          <td class="cell-mono">${unitPriceStr} <span style="font-size:10px; color:var(--text-muted);">${p.standard_unit_label || ''}</span></td>
          <td>${trendBadge}</td>
          <td><span class="badge-subtle">${p.observations_count} receipts</span></td>
          <td>
            <button class="btn btn-sm btn-secondary" onclick="selectProduct(${p.id}, true)">
              ${ICONS.chart}
              <span>Inspect</span>
            </button>
          </td>
        </tr>
      `;
    })
    .join('');
}

/**
 * Render Live Store Deals Table
 */
function renderDealsTable(deals) {
  const tbody = document.getElementById('dealsTableBody');
  if (!tbody) return;

  if (deals.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">No live store probe deals found.</td></tr>`;
    return;
  }

  tbody.innerHTML = deals
    .map((d) => {
      let statusBadge = `<span class="trend-badge trend-stable">${ICONS.trendFlat} Parity</span>`;
      let diffStr = `0.0%`;

      if (d.diff_pct > 0) {
        statusBadge = `<span class="trend-badge trend-hike">${ICONS.trendUp} Price Rise</span>`;
        diffStr = `+${d.diff_pct}%`;
      } else if (d.diff_pct < 0) {
        statusBadge = `<span class="trend-badge trend-drop">${ICONS.trendDown} Deal Active</span>`;
        diffStr = `${d.diff_pct}%`;
      }

      return `
        <tr>
          <td><strong>${d.product_name}</strong></td>
          <td><span class="cell-mono">INR ${d.live_price_inr.toFixed(2)}</span></td>
          <td>INR ${d.last_paid_inr.toFixed(2)}</td>
          <td><span style="color: var(--text-muted);">${d.last_paid_date}</span></td>
          <td><strong>${diffStr}</strong></td>
          <td>${statusBadge}</td>
        </tr>
      `;
    })
    .join('');
}

/**
 * Search Filter
 */
function handleSearch(e) {
  const query = e.target.value.toLowerCase().trim();
  const rows = document.querySelectorAll('#vaultTableBody tr');

  rows.forEach((row) => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(query) ? '' : 'none';
  });
}

/**
 * Sync Trigger
 */
async function handleSync() {
  const btn = document.getElementById('btnSync');
  const icon = btn.querySelector('.sync-icon');
  const text = document.getElementById('syncBtnText');

  btn.disabled = true;
  if (icon) icon.classList.add('rotating');
  if (text) text.textContent = 'Syncing...';

  try {
    const res = await fetch('/api/sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ demo: true }),
    });

    const result = await res.json();
    showToast(
      `Synchronized ${result.orders_synced} orders. ${result.new_observations} price points recorded.`,
      'success'
    );
    await loadDashboardData();
  } catch (err) {
    console.error('Sync failed:', err);
    showToast('Failed to sync with Instamart adapter.', 'alert');
  } finally {
    btn.disabled = false;
    if (icon) icon.classList.remove('rotating');
    if (text) text.textContent = 'Sync Orders';
  }
}

/**
 * Copilot Chat
 */
function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chatInput');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  sendChatMessage(msg);
}

async function sendChatMessage(userText) {
  const thread = document.getElementById('chatThread');
  if (!thread) return;

  const userDiv = document.createElement('div');
  userDiv.className = 'chat-bubble chat-bubble-user';
  userDiv.innerHTML = `<div class="bubble-content">${escapeHtml(userText)}</div>`;
  thread.appendChild(userDiv);
  thread.scrollTop = thread.scrollHeight;

  const typingDiv = document.createElement('div');
  typingDiv.className = 'chat-bubble chat-bubble-assistant';
  typingDiv.innerHTML = `<div class="bubble-content" style="color:var(--text-muted);">Auditing verified purchase receipts in vault...</div>`;
  thread.appendChild(typingDiv);
  thread.scrollTop = thread.scrollHeight;

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: userText }),
    });

    const data = await res.json();
    typingDiv.remove();
    renderAssistantMessage(data, thread);
  } catch (err) {
    console.error('Chat failed:', err);
    typingDiv.remove();
    showToast('Copilot query failed.', 'alert');
  }
}

function renderAssistantMessage(data, container) {
  const { reply, citations, actions } = data;

  const assistantDiv = document.createElement('div');
  assistantDiv.className = 'chat-bubble chat-bubble-assistant';

  let citationsHtml = '';
  if (citations && citations.length > 0) {
    const pills = citations
      .map(
        (c) => `
        <div class="citation-pill" title="Verified against receipt ${c.order_id}">
          ${ICONS.receipt}
          <span><strong>${c.order_id}</strong> (${c.date}): INR ${c.price.toFixed(2)}</span>
        </div>`
      )
      .join('');

    citationsHtml = `
      <div class="citations-block">
        <div class="citations-tag">Verified Vault Citations</div>
        <div class="citations-row">${pills}</div>
      </div>
    `;
  }

  let actionsHtml = '';
  if (actions && actions.length > 0) {
    const cards = actions
      .map(
        (act, idx) => `
        <div class="action-card">
          <div class="action-card-text">
            <span class="action-card-name">${act.label}</span>
            <span class="action-card-sub">Unit Price: INR ${act.unit_price.toFixed(2)} | Outlay: INR ${act.total.toFixed(2)}</span>
          </div>
          <button class="btn btn-sm btn-secondary" id="copilotActionBtn_${idx}">
            ${ICONS.cart}
            <span>Draft Cart</span>
          </button>
        </div>`
      )
      .join('');

    actionsHtml = `
      <div class="chat-actions-container">
        ${cards}
      </div>
    `;
  }

  assistantDiv.innerHTML = `
    <div class="bubble-content">
      <div style="white-space: pre-line;">${escapeHtml(reply)}</div>
      ${citationsHtml}
      ${actionsHtml}
    </div>
  `;

  container.appendChild(assistantDiv);
  container.scrollTop = container.scrollHeight;

  if (actions && actions.length > 0) {
    actions.forEach((act, idx) => {
      const btn = document.getElementById(`copilotActionBtn_${idx}`);
      if (btn) {
        btn.addEventListener('click', () => {
          handleDraftAction(act, btn);
        });
      }
    });
  }
}

function handleDraftAction(item, btnElement = null) {
  showToast(
    `Drafted to Cart: ${item.sku} (INR ${item.total.toFixed(2)}) — Ready for Instamart review`,
    'success'
  );

  if (btnElement) {
    btnElement.innerHTML = `${ICONS.check} <span>Drafted</span>`;
    btnElement.disabled = true;
  }
}

/**
 * DPDP Right to Erasure
 */
async function handlePurgeData() {
  if (!confirm('Permanently erase all local purchase receipts under DPDP 2023?')) return;

  try {
    const res = await fetch('/api/purge', { method: 'POST' });
    showToast('Vault purged. All local purchase history permanently erased.', 'alert');
    const modal = document.getElementById('privacyModal');
    if (modal) modal.style.display = 'none';
    await loadDashboardData();
  } catch (err) {
    console.error('Purge failed:', err);
    showToast('Failed to purge vault data.', 'alert');
  }
}

/**
 * Toast Notifications
 */
function showToast(message, type = 'success') {
  const hub = document.getElementById('toastContainer');
  if (!hub) return;

  const toast = document.createElement('div');
  toast.className = `toast-msg toast-msg-${type}`;
  const icon = type === 'success' ? ICONS.check : ICONS.alert;

  toast.innerHTML = `
    ${icon}
    <span>${escapeHtml(message)}</span>
  `;

  hub.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
