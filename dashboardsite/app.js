/**
 * WhiteMagic Dashboard JavaScript
 * 
 * Simple vanilla JS for dashboard functionality.
 */

// Configuration
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000' 
    : 'https://api.whitemagic.dev';

// State
let currentApiKey = localStorage.getItem('whitemagic_api_key') || '';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    if (currentApiKey) {
        showDashboard();
        loadDashboardData();
    } else {
        showLogin();
    }
});

// Authentication
function login(event) {
    event.preventDefault();
    const apiKey = document.getElementById('apiKey').value;
    
    // Test the API key by fetching account info
    fetch(`${API_BASE_URL}/dashboard/account`, {
        headers: {
            'Authorization': `Bearer ${apiKey}`,
        },
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Invalid API key');
        }
        return response.json();
    })
    .then(data => {
        // Valid key!
        currentApiKey = apiKey;
        localStorage.setItem('whitemagic_api_key', apiKey);
        showDashboard();
        loadDashboardData();
    })
    .catch(error => {
        alert('Authentication failed. Please check your API key.');
        console.error(error);
    });
}

function logout() {
    currentApiKey = '';
    localStorage.removeItem('whitemagic_api_key');
    showLogin();
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
}

// Load dashboard data
async function loadDashboardData() {
    try {
        await Promise.all([
            loadAccountInfo(),
            loadApiKeys(),
        ]);
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        if (error.message.includes('401')) {
            logout();
        }
    }
}

async function loadAccountInfo() {
    const response = await fetch(`${API_BASE_URL}/dashboard/account`, {
        headers: {
            'Authorization': `Bearer ${currentApiKey}`,
        },
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    
    // Update account info
    document.getElementById('accountEmail').textContent = data.account.email;
    document.getElementById('accountPlan').innerHTML = 
        `<span class="inline-flex rounded-full px-2 text-xs font-semibold leading-5 bg-green-100 text-green-800">${data.account.plan_tier}</span>`;
    document.getElementById('accountCreated').textContent = 
        new Date(data.account.created_at).toLocaleDateString();
    document.getElementById('accountSubscription').textContent = 
        data.account.has_subscription ? 'Active' : 'None';
    
    // Update usage stats
    const usage = data.usage;
    const limits = usage.limits;
    
    // Requests today
    document.getElementById('usageRequestsToday').textContent = usage.requests_today;
    document.getElementById('limitDaily').textContent = limits.daily;
    document.getElementById('progressRequestsToday').style.width = 
        `${Math.min(usage.usage_percent.requests_today, 100)}%`;
    
    // Requests this month
    document.getElementById('usageRequestsMonth').textContent = usage.requests_this_month;
    document.getElementById('limitMonthly').textContent = limits.monthly;
    document.getElementById('progressRequestsMonth').style.width = 
        `${Math.min(usage.usage_percent.requests_month, 100)}%`;
    
    // Memories
    document.getElementById('usageMemories').textContent = usage.memories_count;
    document.getElementById('limitMemories').textContent = limits.memories;
    document.getElementById('progressMemories').style.width = 
        `${Math.min(usage.usage_percent.memories, 100)}%`;
    
    // Storage
    document.getElementById('usageStorage').textContent = usage.storage_mb;
    document.getElementById('limitStorage').textContent = `${limits.storage_mb} MB`;
    document.getElementById('progressStorage').style.width = 
        `${Math.min(usage.usage_percent.storage, 100)}%`;
    
    // Update progress bar colors based on usage
    updateProgressBarColors('progressRequestsToday', usage.usage_percent.requests_today);
    updateProgressBarColors('progressRequestsMonth', usage.usage_percent.requests_month);
    updateProgressBarColors('progressMemories', usage.usage_percent.memories);
    updateProgressBarColors('progressStorage', usage.usage_percent.storage);
}

function updateProgressBarColors(elementId, percent) {
    const element = document.getElementById(elementId);
    element.classList.remove('bg-indigo-600', 'bg-yellow-500', 'bg-red-600');
    
    if (percent >= 90) {
        element.classList.add('bg-red-600');
    } else if (percent >= 75) {
        element.classList.add('bg-yellow-500');
    } else {
        element.classList.add('bg-indigo-600');
    }
}

async function loadApiKeys() {
    const response = await fetch(`${API_BASE_URL}/dashboard/api-keys`, {
        headers: {
            'Authorization': `Bearer ${currentApiKey}`,
        },
    });
    
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    
    const data = await response.json();
    const container = document.getElementById('apiKeysList');
    
    if (data.keys.length === 0) {
        container.innerHTML = '<p class="text-sm text-gray-500">No API keys yet. Create one to get started!</p>';
        return;
    }
    
    container.innerHTML = data.keys.map(key => `
        <div class="border rounded-lg p-4 flex justify-between items-center">
            <div>
                <div class="flex items-center space-x-2">
                    <code class="text-sm font-mono">${key.key_prefix}...</code>
                    <span class="inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${key.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                        ${key.is_active ? 'Active' : 'Revoked'}
                    </span>
                </div>
                <p class="text-sm text-gray-600 mt-1">${key.name}</p>
                <p class="text-xs text-gray-500 mt-1">
                    Created: ${new Date(key.created_at).toLocaleDateString()}
                    ${key.last_used_at ? `• Last used: ${new Date(key.last_used_at).toLocaleDateString()}` : ''}
                </p>
            </div>
            <div class="flex space-x-2">
                ${key.is_active ? `
                    <button onclick="rotateApiKey('${key.id}')" class="text-sm text-indigo-600 hover:text-indigo-900">
                        Rotate
                    </button>
                    <button onclick="revokeApiKey('${key.id}')" class="text-sm text-red-600 hover:text-red-900">
                        Revoke
                    </button>
                ` : ''}
            </div>
        </div>
    `).join('');
}

// API Key Management
function showCreateKeyModal() {
    document.getElementById('createKeyModal').style.display = 'flex';
}

function hideCreateKeyModal() {
    document.getElementById('createKeyModal').style.display = 'none';
    document.getElementById('keyName').value = '';
}

async function createApiKey(event) {
    event.preventDefault();
    
    const name = document.getElementById('keyName').value;
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/api-keys`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name }),
        });
        
        if (!response.ok) {
            throw new Error('Failed to create API key');
        }
        
        const data = await response.json();
        
        // Show the new key
        document.getElementById('newKeyValue').textContent = data.api_key;
        document.getElementById('newKeyModal').style.display = 'flex';
        
        // Refresh the list
        await loadApiKeys();
        hideCreateKeyModal();
    } catch (error) {
        alert('Error creating API key: ' + error.message);
        console.error(error);
    }
}

function hideNewKeyModal() {
    document.getElementById('newKeyModal').style.display = 'none';
}

function copyNewKey() {
    const keyValue = document.getElementById('newKeyValue').textContent;
    navigator.clipboard.writeText(keyValue)
        .then(() => {
            alert('API key copied to clipboard!');
        })
        .catch(err => {
            console.error('Failed to copy:', err);
            alert('Failed to copy. Please copy manually.');
        });
}

async function revokeApiKey(keyId) {
    if (!confirm('Are you sure you want to revoke this API key? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/api-keys/${keyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
            },
        });
        
        if (!response.ok) {
            throw new Error('Failed to revoke API key');
        }
        
        alert('API key revoked successfully');
        await loadApiKeys();
    } catch (error) {
        alert('Error revoking API key: ' + error.message);
        console.error(error);
    }
}

async function rotateApiKey(keyId) {
    if (!confirm('This will create a new API key and revoke the old one. Continue?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/dashboard/api-keys/${keyId}/rotate`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
            },
        });
        
        if (!response.ok) {
            throw new Error('Failed to rotate API key');
        }
        
        const data = await response.json();
        
        // Show the new key
        document.getElementById('newKeyValue').textContent = data.new_api_key;
        document.getElementById('newKeyModal').style.display = 'flex';
        
        // Refresh the list
        await loadApiKeys();
    } catch (error) {
        alert('Error rotating API key: ' + error.message);
        console.error(error);
    }
}
