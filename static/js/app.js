/* =========================================================
   SNAPREPORT — SHARED JAVASCRIPT UTILITIES
   ========================================================= */

/* =========================================================
   TOAST NOTIFICATIONS
   ========================================================= */

// Create toast container if it doesn't exist.
function getToastContainer() {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return container;
}

/**
 * Show a toast notification.
 * @param {string} message - The message to display.
 * @param {'success'|'error'|'info'} type - Toast type.
 * @param {number} duration - Auto-dismiss in ms (default 4000).
 */
function showToast(message, type = 'info', duration = 4000) {
    const container = getToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

    toast.innerHTML = `
        <span>${icon}</span>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()" aria-label="Close">×</button>
    `;

    container.appendChild(toast);

    // Auto-dismiss.
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}


/* =========================================================
   CONFIRM MODAL
   ========================================================= */

/**
 * Show a confirmation modal.
 * @param {string} title - Modal title.
 * @param {string} message - Confirmation message.
 * @returns {Promise<boolean>} True if confirmed, false if cancelled.
 */
function showConfirm(title, message) {
    return new Promise((resolve) => {
        // Create backdrop.
        const backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop active';

        backdrop.innerHTML = `
            <div class="modal" style="max-width: 420px;">
                <div class="modal-header">
                    <h3>${title}</h3>
                </div>
                <div class="modal-body">
                    <p style="color: var(--color-text-secondary); font-size: var(--text-sm);">
                        ${message}
                    </p>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-ghost" id="confirmCancel">Cancel</button>
                    <button class="btn btn-danger" id="confirmOk">Confirm</button>
                </div>
            </div>
        `;

        document.body.appendChild(backdrop);

        // Event handlers.
        backdrop.querySelector('#confirmCancel').onclick = () => {
            backdrop.remove();
            resolve(false);
        };

        backdrop.querySelector('#confirmOk').onclick = () => {
            backdrop.remove();
            resolve(true);
        };

        // Close on backdrop click.
        backdrop.onclick = (e) => {
            if (e.target === backdrop) {
                backdrop.remove();
                resolve(false);
            }
        };

        // Close on Escape.
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                backdrop.remove();
                resolve(false);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    });
}


/* =========================================================
   API HELPER
   ========================================================= */

/**
 * Make an API request with automatic error handling.
 * @param {string} url - The endpoint URL.
 * @param {object} options - Fetch options (method, body, etc.).
 * @returns {Promise<object>} The parsed JSON response.
 */
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Something went wrong.');
        }

        return data;

    } catch (error) {
        if (error.message === 'Failed to fetch') {
            throw new Error('Unable to connect to the server.');
        }
        throw error;
    }
}

/**
 * POST JSON data to an endpoint.
 */
async function apiPost(url, body) {
    return apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(body)
    });
}

/**
 * PUT JSON data to an endpoint.
 */
async function apiPut(url, body) {
    return apiRequest(url, {
        method: 'PUT',
        body: JSON.stringify(body)
    });
}

/**
 * DELETE a resource.
 */
async function apiDelete(url) {
    return apiRequest(url, {
        method: 'DELETE'
    });
}


/* =========================================================
   BUTTON LOADING STATE
   ========================================================= */

/**
 * Set a button to loading state.
 * @param {HTMLElement} btn - The button element.
 * @param {boolean} loading - Whether to show loading.
 */
function setButtonLoading(btn, loading) {
    if (loading) {
        btn.disabled = true;
        btn.classList.add('btn-loading');
        btn.dataset.originalText = btn.innerHTML;
    } else {
        btn.disabled = false;
        btn.classList.remove('btn-loading');
        if (btn.dataset.originalText) {
            btn.innerHTML = btn.dataset.originalText;
        }
    }
}


/* =========================================================
   INITIALIZATION
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {
    // Add active state to current nav link.
    const currentPath = window.location.pathname;
    document.querySelectorAll('.header-nav a').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
});
