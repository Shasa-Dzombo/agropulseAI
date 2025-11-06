// JavaScript for Federation Page

document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('nvr_token');
    if (!token) { window.location.href = '/login'; return; }
    const headers = { 'Authorization': `Bearer ${token}` };

    const nodeList = document.getElementById('node-list');

    function fetchFederationStatus() {
        fetch('/api/federation/status', { headers })
            .then(res => res.json())
            .then(nodes => {
                nodeList.innerHTML = '';
                for (const name in nodes) {
                    const node = nodes[name];
                    const nodeEl = document.createElement('div');
                    nodeEl.className = 'node-item';
                    nodeEl.innerHTML = `
                        <strong>${node.name}</strong> (${node.node_type}) - ${node.ip_address}:${node.api_port}
                        <span class="status-${node.status.toLowerCase()}">${node.status}</span>
                    `;
                    nodeList.appendChild(nodeEl);
                }
            })
            .catch(err => console.error('Failed to fetch federation status:', err));
    }

    fetchFederationStatus();
    setInterval(fetchFederationStatus, 15000); // Refresh every 15 seconds
});
