// JavaScript for the login page

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const errorElement = document.getElementById('login-error');

    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        errorElement.textContent = '';

        const formData = new FormData(loginForm);
        
        fetch('/api/token', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Login failed. Please check your username and password.');
            }
            return response.json();
        })
        .then(data => {
            localStorage.setItem('nvr_token', data.access_token);
            window.location.href = '/';
        })
        .catch(error => {
            errorElement.textContent = error.message;
        });
    });
});
