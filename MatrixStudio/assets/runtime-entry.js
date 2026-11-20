// Optional local handover when an older preview still serves the shared UI files.
fetch('/assets/local-session.json', {cache: 'no-store'})
  .then(response => response.ok ? response.json() : null)
  .then(session => {
    if (!session || !Number.isInteger(session.port) || session.port < 1024 || session.port > 65535) return;
    if (!['127.0.0.1', 'localhost'].includes(location.hostname)) return;
    if (Number(location.port) === session.port) return;
    const target = new URL(location.href);
    target.port = String(session.port);
    location.replace(target.href);
  })
  .catch(() => {});
