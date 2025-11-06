// JavaScript for Incidents Page

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('nvr_token');
    if (!token) { window.location.href = '/login'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };

    const incidentList = document.getElementById('incident-list');

    function fetchIncidents() {
        fetch('/api/incidents/open', { headers })
            .then(res => res.json())
            .then(incidents => {
                incidentList.innerHTML = '';
                incidents.forEach(incident => {
                    const incidentEl = document.createElement('div');
                    incidentEl.className = 'incident-item';
                    incidentEl.innerHTML = `
                        <h4>${incident.title}</h4>
                        <p>Status: ${incident.status} | Severity: ${incident.severity}</p>
                        <p>Created: ${new Date(incident.created_at).toLocaleString()}</p>
                    `;
                    incidentList.appendChild(incidentEl);
                });
            })
            .catch(err => console.error('Failed to fetch incidents:', err));
    }

    fetchIncidents();
});
