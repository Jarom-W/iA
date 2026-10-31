'use strict';
const zone = document.body.dataset.timezone;
const currency = document.body.dataset.currency;
const wall = document.querySelector('[data-wall-clock]');
const clockFormat = new Intl.DateTimeFormat('en-US', {timeZone: zone, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false});
function wallTick() { if (wall) wall.textContent = clockFormat.format(new Date()); }
wallTick();
setInterval(wallTick, 1000);
document.querySelector('[data-print]')?.addEventListener('click', () => window.print());
const card = document.querySelector('[data-timer-card]');
if (card) {
  let started = Number(card.dataset.start);
  let ended = Number(card.dataset.end);
  let rate = Number(card.dataset.rate);
  let server = Number(card.dataset.server);
  let anchor = performance.now();
  let entryId = card.dataset.entryId;
  let status = card.dataset.status;
  const digits = card.querySelector('[data-elapsed]');
  const amount = card.querySelector('[data-earnings]');
  const message = card.querySelector('[data-sync-message]');
  function render() {
    const seconds = started ? Math.max(0, Math.floor((ended || server + (performance.now() - anchor) / 1000) - started)) : 0;
    digits.textContent = [Math.floor(seconds / 3600), Math.floor(seconds / 60) % 60, seconds % 60].map(n => String(n).padStart(2, '0')).join(':');
    const cents = Math.round(seconds * rate / 3600);
    amount.textContent = new Intl.NumberFormat('en-US', {style: 'currency', currency, currencyDisplay: 'code'}).format(cents / 100);
  }
  let syncing = false;
  async function sync() {
    if (syncing || document.hidden) return;
    syncing = true;
    try {
      const response = await fetch('/api/timer', {credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(6000)});
      if (!response.ok || !response.headers.get('content-type')?.includes('application/json')) {
        message.textContent = 'Session expired or unavailable. Reload to reconnect; your timer is stored on the server.';
        return;
      }
      const data = await response.json();
      if ((data.entry?.id || '') !== entryId || (data.entry?.status || '') !== status) {
        location.reload();
        return;
      }
      server = data.server_now;
      anchor = performance.now();
      if (data.entry) { started = data.entry.started_at; ended = data.entry.ended_at; rate = data.entry.rate_cents; }
      message.textContent = status === 'draft' ? 'Timer stopped. Finish your work log to make this session report-ready.' : 'Your time stays with you, even when you close this tab.';
      render();
    } catch {
      message.textContent = 'Connection interrupted. Showing the last known timer; reconnect before clocking out.';
    } finally { syncing = false; }
  }
  render();
  setInterval(render, 1000);
  setInterval(sync, 15000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) sync(); });
  window.addEventListener('online', sync);
  window.addEventListener('pageshow', event => { if (event.persisted) sync(); });
}
// Keep an unfinished journal on the server and warn before discarding typed text.
// No client data or credentials are persisted in browser storage.
const journal = document.querySelector('[data-journal]');
if (journal) {
  let dirty = false;
  journal.addEventListener('input', () => { dirty = true; });
  journal.addEventListener('submit', () => { dirty = false; });
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
}
