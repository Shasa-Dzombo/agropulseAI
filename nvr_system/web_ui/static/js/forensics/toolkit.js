// JavaScript for Forensics Toolkit

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('nvr_token');
    if (!token) { window.location.href = '/login'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };

    const trackPathBtn = document.getElementById('track-path-btn');
    const eventIdInput = document.getElementById('event-id-input');
    const pathResults = document.getElementById('path-results');

    trackPathBtn.addEventListener('click', () => {
        const eventId = eventIdInput.value;
        if (!eventId) {
            alert('Please enter an event ID.');
            return;
        }
        pathResults.innerHTML = '<p>Tracking path...</p>';
        fetch(`/api/forensics/track_path/${eventId}`, { headers })
            .then(res => res.json())
            .then(data => {
                pathResults.innerHTML = `
                    <h4>Path Results:</h4>
                    <pre>${JSON.stringify(data, null, 2)}</pre>
                `;
            })
            .catch(err => {
                console.error('Path tracking failed:', err);
                pathResults.innerHTML = '<p>Error tracking path.</p>';
            });
    });

    // Placeholder for synopsis generation
});
