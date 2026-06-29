document.addEventListener('DOMContentLoaded', function() {
    console.log('%c OT-ICS Security Lab ', 'background: #0a0e17; color: #00d4ff; font-size: 16px; font-weight: bold;');
    console.log('%c FOR ISOLATED EDUCATIONAL USE ONLY ', 'background: #1a0000; color: #ff6b6b; font-size: 12px;');

    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(el => new bootstrap.Tooltip(el));

    const servicesRefresh = document.getElementById('refresh-services');
    if (servicesRefresh) {
        servicesRefresh.addEventListener('click', function() {
            fetch('/api/services/status')
                .then(r => r.json())
                .then(data => {
                    data.services.forEach(s => {
                        const badge = document.querySelector(`.service-badge[data-service-id="${s.id}"]`);
                        if (badge) {
                            badge.textContent = s.status;
                            badge.className = `badge ${s.status === 'running' ? 'bg-success' : 'bg-secondary'} service-badge`;
                        }
                    });
                });
        });
    }
});
