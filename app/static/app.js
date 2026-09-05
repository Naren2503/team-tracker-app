function showNotice(message, isError = false) {
  const notice = document.getElementById('notice');
  if (!notice) return;
  notice.hidden = false;
  notice.textContent = message;
  notice.style.background = isError ? 'rgba(180,35,24,.1)' : 'rgba(23,107,93,.1)';
}

function filterTable(inputId, tableId) {
  const term = document.getElementById(inputId).value.toLowerCase();
  document.querySelectorAll(`#${tableId} tbody tr`).forEach((row) => {
    row.style.display = row.textContent.toLowerCase().includes(term) ? '' : 'none';
  });
}

function monthBounds(month) {
  if (!month) return {};
  const [year, number] = month.split('-').map(Number);
  const lastDay = new Date(year, number, 0).getDate();
  return { start: `${month}-01`, end: `${month}-${String(lastDay).padStart(2, '0')}` };
}

function setStatusPie(element, counts) {
  if (!element) return;
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0) || 1;
  let offset = 0;
  const segments = [['completed', counts.completed], ['in-progress', counts.in_progress], ['pending', counts.pending], ['blocked', counts.blocked]].map(([name, value]) => {
    const next = offset + value / total * 100;
    const segment = `var(--chart-${name}) ${offset}% ${next}%`;
    offset = next;
    return segment;
  });
  element.style.background = `conic-gradient(${segments.join(', ')})`;
}

function renderTrendline(element, trend) {
  if (!element) return;
  const values = Object.values(trend).map((row) => row.hours);
  if (!values.length) { element.innerHTML = ''; return; }
  const max = Math.max(...values, 1);
  const labels = Object.keys(trend);
  const chartWidth = 720;
  const x = (index) => 40 + index * (chartWidth / Math.max(values.length - 1, 1));
  const points = values.map((value, index) => `${x(index)},${215 - value / max * 175}`).join(' ');
  element.innerHTML = `<polyline points="${points}" fill="none" stroke="var(--accent)" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" />${values.map((value, index) => `<circle cx="${x(index)}" cy="${215 - value / max * 175}" r="6" fill="var(--accent-2)" /><text x="${x(index)}" y="${195 - value / max * 175}" text-anchor="middle" class="trend-value">${value}h</text><text x="${x(index)}" y="250" text-anchor="middle" class="trend-label">${labels[index]}</text>`).join('')}`;
}

function renderSeriesLine(element, trend, series) {
  if (!element) return;
  const labels = Object.keys(trend);
  if (!labels.length) { element.innerHTML = ''; return; }
  const width = 720;
  const x = (index) => 40 + index * (width / Math.max(labels.length - 1, 1));
  const max = Math.max(...series.flatMap((item) => labels.map((label) => trend[label][item.key] || 0)), 1);
  const lines = series.map((item) => {
    const points = labels.map((label, index) => `${x(index)},${220 - (trend[label][item.key] || 0) / max * 170}`).join(' ');
    return `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />${labels.map((label, index) => { const value = trend[label][item.key] || 0; return `<circle cx="${x(index)}" cy="${220 - value / max * 170}" r="5" fill="${item.color}" /><text x="${x(index)}" y="${205 - value / max * 170}" text-anchor="middle" class="trend-value">${value}</text>`; }).join('')}`;
  }).join('');
  element.innerHTML = `${lines}${labels.map((label, index) => `<text x="${x(index)}" y="255" text-anchor="middle" class="trend-label">${label}</text>`).join('')}`;
}

function scaleMixChart(element) {
  if (!element) return;
  const bars = [...element.querySelectorAll('.mix-bars i')];
  const values = bars.map((bar) => Number.parseFloat(bar.dataset.value) || 0);
  const max = Math.max(...values, 1);
  bars.forEach((bar) => {
    const value = Number.parseFloat(bar.dataset.value) || 0;
    bar.dataset.value = value;
    bar.style.height = `${value ? 10 + value / max * 140 : 4}px`;
  });
}

function rememberFilters() {
  const view = document.body.dataset.view || 'dashboard';
  const values = {};
  ['testerFilter', 'statusFilter', 'monthlyMonthFilter', 'startMonthFilter', 'endMonthFilter', 'weekMonthFilter', 'weekFilter', 'granularityFilter', 'trackerTesterFilter', 'trackerStartDateFilter', 'trackerEndDateFilter'].forEach((id) => {
    const element = document.getElementById(id);
    if (element) values[id] = element.value;
  });
  sessionStorage.setItem('team-tracker-filters', JSON.stringify(values));
}

function restoreFilters() {
  try {
    const values = JSON.parse(sessionStorage.getItem('team-tracker-filters') || '{}');
    Object.entries(values).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.value = value;
    });
  } catch (error) {
    sessionStorage.removeItem('team-tracker-filters');
  }
}

function renderLifecycleLine(element, trend) {
  if (!element) return;
  const labels = Object.keys(trend);
  if (!labels.length) { element.innerHTML = ''; return; }
  const series = [{ key: 'created', color: 'var(--accent-2)' }, { key: 'resolved', color: 'var(--accent)' }, { key: 'backlog', color: '#8b9a92' }];
  const width = 720;
  const x = (index) => 40 + index * (width / Math.max(labels.length - 1, 1));
  const max = Math.max(...series.flatMap((item) => labels.map((label) => trend[label][item.key])), 1);
  element.innerHTML = series.map((item) => {
    const points = labels.map((label, index) => `${x(index)},${220 - trend[label][item.key] / max * 170}`).join(' ');
    return `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />${labels.map((label, index) => `<circle cx="${x(index)}" cy="${220 - trend[label][item.key] / max * 170}" r="5" fill="${item.color}" /><text x="${x(index)}" y="${205 - trend[label][item.key] / max * 170}" text-anchor="middle" class="trend-value">${trend[label][item.key]}</text>`).join('')}`;
  }).join('') + labels.map((label, index) => `<text x="${x(index)}" y="255" text-anchor="middle" class="trend-label">${label}</text>`).join('');
}

function syncWeeklyMonth() {
  const start = document.getElementById('startMonthFilter');
  const end = document.getElementById('endMonthFilter');
  if (document.getElementById('granularityFilter')?.value === 'week' && start?.value && !end?.value) end.value = start.value;
}

async function refreshDashboard() {
  rememberFilters();
  const view = document.body.dataset.view || 'dashboard';
  const tester = document.getElementById('testerFilter')?.value || '';
  const status = document.getElementById('statusFilter')?.value || '';
  const granularity = view === 'weekly' ? 'week' : (document.getElementById('granularityFilter')?.value || 'month');
  const monthlyBounds = monthBounds(document.getElementById('monthlyMonthFilter')?.value);
  const startBounds = monthBounds(document.getElementById('startMonthFilter')?.value);
  const endBounds = monthBounds(document.getElementById('endMonthFilter')?.value);
  const weekBounds = monthBounds(document.getElementById('weekMonthFilter')?.value);
  const utilizationBounds = monthBounds(document.getElementById('utilizationMonthFilter')?.value);
  const week = document.getElementById('weekFilter')?.value || '';
  const params = new URLSearchParams();
  if (tester) params.set('tester', tester);
  if (status) params.set('status', status);
  if (startBounds.start) params.set('start', startBounds.start);
  if (endBounds.end) params.set('end', endBounds.end);
  if (monthlyBounds.start) { params.set('start', monthlyBounds.start); params.set('end', monthlyBounds.end); }
  if (weekBounds.start) { params.set('start', weekBounds.start); params.set('end', weekBounds.end); }
  if (utilizationBounds.start) { params.set('start', utilizationBounds.start); params.set('end', utilizationBounds.end); }
  if (week) params.set('week', week);
  params.set('granularity', granularity);
  const response = await fetch(`/api/dashboard/metrics?${params}`);
  if (!response.ok) return showNotice('Unable to refresh dashboard', true);
  const data = await response.json();
  const cards = document.getElementById('cards');
  if (cards) cards.innerHTML = [
    ['Total Records', data.total_records],
    ['Completed', data.status_counts.completed],
    ['In Progress', data.status_counts.in_progress],
    ['Blocked', data.status_counts.blocked],
    ['Total Hours', data.total_hours],
    ['Passed TC', data.passed_tc],
    ['Avg Ticket Age', `${data.average_age_days}d`],
  ].map(([label, value]) => `<article><span>${label}</span><strong>${value}</strong></article>`).join('');
  const trendTitle = document.getElementById('trendTitle');
  if (trendTitle) trendTitle.textContent = `${granularity === 'week' ? 'Weekly' : 'Monthly'} Effort Trend`;
  const trendChart = document.getElementById('trendChart');
  if (trendChart) trendChart.innerHTML = Object.entries(data.trend).map(([label, row]) => `<button><span>${label}</span><i style="width: ${row.hours}%"></i><b>${row.hours}h</b></button>`).join('');
  const monthlyMixChart = document.getElementById('monthlyMixChart');
  if (monthlyMixChart) monthlyMixChart.innerHTML = Object.entries(data.trend).map(([label, row]) => `<div class="mix-group"><strong>${label}</strong><div class="mix-bars"><i class="tickets" data-value="${row.tickets || 0}" title="Tickets: ${row.tickets || 0}"></i><i class="cases" data-value="${(row.passed_tc || 0) + (row.failed_tc || 0)}" title="Test cases: ${(row.passed_tc || 0) + (row.failed_tc || 0)}"></i><i class="steps" data-value="${row.steps || 0}" title="Test steps: ${row.steps || 0}"></i></div><small>Tickets ${row.tickets || 0} | TC ${(row.passed_tc || 0) + (row.failed_tc || 0)} | Steps ${row.steps || 0}</small></div>`).join('');
  const sixMonthChart = document.getElementById('sixMonthChart');
  if (sixMonthChart) sixMonthChart.innerHTML = Object.entries(data.history_trend || {}).map(([label, row]) => `<div class="mix-group"><strong>${label}</strong><div class="mix-bars"><i class="tickets" data-value="${row.tickets || 0}" title="Tickets: ${row.tickets || 0}"></i><i class="cases" data-value="${(row.passed_tc || 0) + (row.failed_tc || 0)}" title="Test cases: ${(row.passed_tc || 0) + (row.failed_tc || 0)}"></i><i class="steps" data-value="${row.steps || 0}" title="Test steps: ${row.steps || 0}"></i></div><small>Tickets ${row.tickets || 0} | TC ${(row.passed_tc || 0) + (row.failed_tc || 0)} | Steps ${row.steps || 0}</small></div>`).join('');
  scaleMixChart(monthlyMixChart);
  scaleMixChart(sixMonthChart);
  document.querySelectorAll('.chart-legend').forEach((legend) => {
    if (legend.closest('section')?.querySelector('#monthlyMixChart, #sixMonthChart')) legend.innerHTML = '<span><i class="tickets"></i>Tickets</span><span><i class="cases"></i>Test Cases</span><span><i class="steps"></i>Test Steps</span>';
  });
  renderTrendline(document.getElementById('trendLine'), data.trend);
  renderLifecycleLine(document.getElementById('lifecycleLine'), data.lifecycle_trend || {});
  const utilizationCards = document.getElementById('utilizationCards');
  if (utilizationCards) utilizationCards.innerHTML = [['Total Testers', data.total_testers], ['Total Hours', data.total_hours], ['Average Utilization', `${data.average_utilization}%`]].map(([label, value]) => `<article><span>${label}</span><strong>${value}</strong></article>`).join('');
  const weeklyCards = document.getElementById('weeklyCards');
  if (weeklyCards) weeklyCards.innerHTML = [['Total Tickets', data.total_records], ['Test Cases', data.passed_tc + data.failed_tc], ['Test Steps', data.passed_steps + data.failed_steps]].map(([label, value]) => `<article><span>${label}</span><strong>${value}</strong></article>`).join('');
  const utilizationChart = document.getElementById('utilizationChart');
  if (utilizationChart) utilizationChart.innerHTML = Object.entries(data.utilization).map(([label, value]) => `<button><span>${label}</span><i style="width: ${Math.min(value, 100)}%"></i><b>${value}%</b></button>`).join('');
  const ageList = document.querySelector('.age-list');
  if (ageList) ageList.innerHTML = data.ticket_ageing.slice(0, 8).map((ticket) => `<div><span>${ticket.ticket_id}</span><b>${ticket.age_days ?? '-'}d</b></div>`).join('');
  const ageSummary = document.getElementById('ageSummary');
  if (ageSummary) ageSummary.innerHTML = data.ticket_ageing.slice(0, 8).map((ticket) => `<div><span>${ticket.ticket_id} · ${ticket.tester}</span><b>${ticket.age_days ?? '-'}d</b></div>`).join('');
  const statusSummary = document.getElementById('statusSummary');
  if (statusSummary) statusSummary.innerHTML = [['Completed', data.status_counts.completed], ['In progress', data.status_counts.in_progress], ['Pending', data.status_counts.pending], ['Blocked', data.status_counts.blocked]].map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`).join('');
  const testerSummary = document.getElementById('testerSummary');
  if (testerSummary) testerSummary.innerHTML = Object.entries(data.by_tester).map(([label, count]) => `<div><span>${label}</span><b>${count} tickets</b></div>`).join('');
  const reportTickets = document.querySelector('#reportTickets tbody');
  if (reportTickets) reportTickets.innerHTML = data.ticket_ageing.map((ticket) => `<tr><td>${ticket.ticket_id}</td><td>${ticket.tester}</td><td>${ticket.start_date || '-'}</td><td>${ticket.end_date || '-'}</td><td><span class="pill">${ticket.status}</span></td><td>${ticket.age_days ?? '-'}d</td><td class="comment">${ticket.comments}</td></tr>`).join('');
  showNotice('Dashboard refreshed');
}

function refreshTracker() {
  rememberFilters();
  const startDate = document.getElementById('trackerStartDateFilter')?.value || '';
  const endDate = document.getElementById('trackerEndDateFilter')?.value || '';
  const tester = document.getElementById('trackerTesterFilter')?.value || '';
  const counts = { completed: 0, in_progress: 0, pending: 0, blocked: 0 };
  let totalVisible = 0;
  document.querySelectorAll('#trackerTable tbody tr').forEach((row) => {
    const matchesTester = !tester || row.dataset.tester === tester;
    const matchesStart = !startDate || row.dataset.startDate >= startDate;
    const matchesEnd = !endDate || row.dataset.startDate <= endDate;
    const visible = matchesTester && matchesStart && matchesEnd;
    row.style.display = visible ? '' : 'none';
    if (visible) {
      totalVisible++;
      const st = (row.dataset.status || '').toLowerCase();
      if (st.includes('block')) counts.blocked++;
      else if (st.includes('progress')) counts.in_progress++;
      else if (st.includes('complete')) counts.completed++;
      else counts.pending++;
    }
  });
  const statusChart = document.getElementById('trackerStatusChart');
  if (statusChart) {
    statusChart.innerHTML = [
      ['Completed', counts.completed],
      ['In progress', counts.in_progress],
      ['On hold', counts.pending],
      ['Blocked', counts.blocked]
    ].map(([label, val]) => `<div class="status-row"><span>${label}</span><i style="width: ${totalVisible ? (val / totalVisible * 100) : 0}%"></i><b>${val}</b></div>`).join('');
  }
}

restoreFilters();
const initialDataElem = document.getElementById('initialMetrics');
if (initialDataElem) {
  try {
    const data = JSON.parse(initialDataElem.textContent);
    if (document.getElementById('trendLine') && data.trend) renderTrendline(document.getElementById('trendLine'), data.trend);
    if (document.getElementById('lifecycleLine') && data.lifecycle_trend) renderLifecycleLine(document.getElementById('lifecycleLine'), data.lifecycle_trend);
    scaleMixChart(document.getElementById('monthlyMixChart'));
    scaleMixChart(document.getElementById('sixMonthChart'));
  } catch (e) {
    console.warn('Initial chart parse warning', e);
  }
}
if (document.getElementById('trackerStatusChart')) refreshTracker();

async function previewImport() {
  const form = document.getElementById('importForm');
  const output = document.getElementById('importPreview');
  const data = new FormData(form);
  const response = await fetch('/api/imports/preview', { method: 'POST', body: data });
  const payload = await response.json();
  output.textContent = JSON.stringify(payload, null, 2);
  showNotice(response.ok ? 'Preview complete' : payload.detail || 'Preview failed', !response.ok);
}

async function syncFromUrl() {
  const urlInput = document.getElementById('syncUrlInput');
  const modeInput = document.getElementById('syncUrlMode');
  const btn = document.getElementById('syncUrlBtn');
  if (!urlInput || !urlInput.value) return;
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Syncing...';
  try {
    const response = await fetch('/api/imports/sync-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: urlInput.value, mode: modeInput ? modeInput.value : 'merge' }),
    });
    const payload = await response.json();
    if (response.ok) {
      showNotice(`Sync successful! ${payload.successful_rows} records updated.`, false);
      setTimeout(() => location.reload(), 1500);
    } else {
      showNotice(payload.detail || 'Sync failed', true);
    }
  } catch (err) {
    showNotice(`Sync error: ${err.message}`, true);
  } finally {
    btn.disabled = false;
    btn.textContent = originalText;
  }
}

const importForm = document.getElementById('importForm');
if (importForm) {
  importForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = new FormData(importForm);
    const response = await fetch('/api/imports', { method: 'POST', body: data });
    const payload = await response.json();
    showNotice(response.ok ? `Import ${payload.status}: ${payload.successful_rows} accepted, ${payload.rejected_rows} rejected` : payload.detail || 'Import failed', !response.ok);
  });
}

const userForm = document.getElementById('userForm');
if (userForm) {
  userForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(userForm));
    payload.role_id = Number(payload.role_id);
    const response = await fetch('/api/admin/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const result = await response.json();
    showNotice(response.ok ? `User created: ${result.email}` : result.detail || 'User creation failed', !response.ok);
  });
}

async function loadUsers() {
  const output = document.getElementById('adminOutput');
  const response = await fetch('/api/admin/users');
  output.textContent = JSON.stringify(await response.json(), null, 2);
}
