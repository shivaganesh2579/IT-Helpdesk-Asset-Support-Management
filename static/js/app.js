(() => {
  const menuButton = document.getElementById('mobile-menu');
  const sidebar = document.getElementById('sidebar');
  if (menuButton && sidebar) {
    menuButton.addEventListener('click', () => sidebar.classList.toggle('sidebar-open'));
  }

  document.querySelectorAll('.flash-close').forEach((button) => {
    button.addEventListener('click', () => button.closest('.flash')?.remove());
  });

  document.querySelectorAll('[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.getAttribute('data-confirm') || 'Are you sure?';
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  document.querySelectorAll('[data-scroll-to]').forEach((button) => {
    button.addEventListener('click', () => {
      const target = document.getElementById(button.getAttribute('data-scroll-to'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        target.querySelector('textarea, input, select')?.focus({ preventScroll: true });
      }
    });
  });

  const ticketType = document.getElementById('ticket-type');
  const incidentFields = document.getElementById('incident-fields');
  const requestFields = document.getElementById('request-fields');
  const refreshTicketFields = () => {
    if (!ticketType || !incidentFields || !requestFields) return;
    const isIncident = ticketType.value === 'Incident';
    incidentFields.classList.toggle('hidden', !isIncident);
    requestFields.classList.toggle('hidden', isIncident);
  };
  ticketType?.addEventListener('change', refreshTicketFields);
  refreshTicketFields();
})();
