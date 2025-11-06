// Main JavaScript for the AgroPulse NVR Web UI

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('nvr_token');
    if (!token) {
        window.location.href = '/login';
        return;
    }

    const headers = { 'Authorization': `Bearer ${token}` };

    // WebSocket connection for real-time updates
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/updates`);

    ws.onopen = () => console.log('WebSocket connected');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('WS message received:', data);
        // Handle real-time updates here (e.g., new event, status change)
    };
    ws.onclose = () => console.log('WebSocket disconnected');

    // Populate search dropdowns
    const searchCamera = document.getElementById('search-camera');
    const searchClass = document.getElementById('search-class');

    fetch('/api/status', { headers })
        .then(res => res.json())
        .then(cameras => {
            searchCamera.innerHTML = '<option value="">All Cameras</option>';
            for (const camId in cameras) {
                const option = document.createElement('option');
                option.value = camId;
                option.textContent = cameras[camId].id;
                searchCamera.appendChild(option);
            }
        });

    fetch('/api/ai/classes', { headers })
        .then(res => res.json())
        .then(classes => {
            searchClass.innerHTML = '<option value="">All Classes</option>';
            classes.forEach(c => {
                const option = document.createElement('option');
                option.value = c;
                option.textContent = c;
                searchClass.appendChild(option);
            });
        });

    // Search functionality
    const searchButton = document.getElementById('search-button');
    searchButton.addEventListener('click', () => {
        const criteria = {
            camera_id: document.getElementById('search-camera').value || null,
            object_class: document.getElementById('search-class').value || null,
            start_time_utc: document.getElementById('search-start-time').value || null,
            end_time_utc: document.getElementById('search-end-time').value || null,
        };

        fetch('/api/events/search', {
            method: 'POST',
            headers: { ...headers, 'Content-Type': 'application/json' },
            body: JSON.stringify(criteria)
        })
        .then(res => res.json())
        .then(events => {
            const eventList = document.getElementById('event-list');
            eventList.innerHTML = '';
            events.forEach(event => {
                const item = document.createElement('div');
                item.className = 'event-item';
                item.innerHTML = `
                    <p><strong>Event:</strong> ${event.event_id}</p>
                    <p><strong>Camera:</strong> ${event.camera_id}</p>
                    <p><strong>Time:</strong> ${new Date(event.timestamp_utc).toLocaleString()}</p>
                    ${event.video_clip_path ? `<a href="/api/events/${event.event_id}/video" target="_blank">View Video</a>` : ''}
                `;
                eventList.appendChild(item);
            });
        });
    });
});
