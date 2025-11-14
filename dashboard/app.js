/**
 * WhiteMagic Dashboard JavaScript
 * 
 * Simple vanilla JS for dashboard functionality.
 */

// Configuration - prioritize explicit overrides
const metaApiBase = document.querySelector('meta[name="whitemagic-api-base"]');
const isLocal = window.location.hostname === 'localhost' || 
                window.location.hostname === '127.0.0.1' ||
                window.location.hostname.startsWith('192.168.');
const API_BASE_URL = window.WHITEMAGIC_API_BASE
    || (metaApiBase && metaApiBase.content.trim())
    || (isLocal ? 'http://localhost:8000' : 'https://api.whitemagic.dev');

console.log('API Base URL:', API_BASE_URL);

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
function retrieveApiKey(event) {
    event.preventDefault();
    const email = document.getElementById('email').value;
    
    // Call API to retrieve/generate API key
    fetch(`${API_BASE_URL}/api/v1/api-keys/retrieve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: email }),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.detail || 'Failed to retrieve API key');
            });
        }
        return response.json();
    })
    .then(data => {
        // Show the API key to the user
        alert(`✅ Your API Key:\n\n${data.api_key}\n\n⚠️ SAVE THIS KEY! It won't be shown again.\n\nYou'll be signed in automatically.`);
        
        // Auto-login with the new key
        currentApiKey = data.api_key;
        localStorage.setItem('whitemagic_api_key', data.api_key);
        showDashboard();
        loadDashboardData();
    })
    .catch(error => {
        alert(`❌ ${error.message}\n\nIf you haven't subscribed yet, visit: https://whop.com/whitemagic`);
        console.error(error);
    });
}

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

function showEmailForm() {
    document.getElementById('emailForm').style.display = 'block';
    document.getElementById('apiKeyForm').style.display = 'none';
}

function showApiKeyForm() {
    document.getElementById('emailForm').style.display = 'none';
    document.getElementById('apiKeyForm').style.display = 'block';
}

function logout() {
    currentApiKey = '';
    localStorage.removeItem('whitemagic_api_key');
    showLogin();
}

function showLogin() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('dashboardContent').style.display = 'none';
    document.getElementById('sidebar').style.display = 'none';
}

function showDashboard() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('dashboardContent').style.display = 'block';
    document.getElementById('sidebar').style.display = 'block';
}

// Load dashboard data
async function loadDashboardData() {
    try {
        await Promise.all([
            loadAccountInfo(),
            loadApiKeys(),
            loadMemories(),
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
    
    // Update account info (hero section and sidebar)
    document.getElementById('accountEmail').textContent = data.account.email;
    document.getElementById('sidebarEmail').textContent = data.account.email;
    
    const planColors = {
        'free': 'bg-mint text-emerald-800',
        'starter': 'bg-lavender text-white',
        'plus': 'bg-lavender text-white',
        'pro': 'bg-peach text-orange-800',
        'enterprise': 'bg-pale-blue text-blue-800'
    };
    const planClass = planColors[data.account.plan_tier] || 'bg-lavender text-white';
    
    document.getElementById('accountPlan').innerHTML = 
        `<span class="inline-flex rounded-full px-2 py-1 text-xs font-semibold ${planClass}">${data.account.plan_tier}</span>`;
    document.getElementById('sidebarPlan').innerHTML = data.account.plan_tier;
    document.getElementById('sidebarPlan').className = `inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${planClass}`;
    
    document.getElementById('accountCreated').textContent = 
        new Date(data.account.created_at).toLocaleDateString();
    
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
    
    // Calculate overall usage percentage (max of all quotas)
    const overallUsage = Math.max(
        usage.usage_percent.requests_month,
        usage.usage_percent.memories,
        usage.usage_percent.storage
    );
    
    // Update hero section
    document.getElementById('overallUsagePercent').textContent = Math.round(overallUsage) + '%';
    document.getElementById('heroRequestCount').textContent = usage.requests_this_month.toLocaleString();
    
    // Update progress bar colors based on usage
    updateProgressBarColors('progressRequestsToday', usage.usage_percent.requests_today);
    updateProgressBarColors('progressRequestsMonth', usage.usage_percent.requests_month);
    updateProgressBarColors('progressMemories', usage.usage_percent.memories);
    updateProgressBarColors('progressStorage', usage.usage_percent.storage);
    
    // Check if upgrade banner should be shown
    checkUpgradeBanner(data.account, usage);
    
    // Load usage chart
    loadUsageChart(7);
}

function updateProgressBarColors(elementId, percent) {
    const element = document.getElementById(elementId);
    element.classList.remove('bg-lavender', 'bg-yellow-500', 'bg-red-600');
    
    if (percent >= 90) {
        element.classList.add('bg-red-600');
    } else if (percent >= 75) {
        element.classList.add('bg-yellow-500');
    } else {
        element.classList.add('bg-lavender');
    }
}

// Sidebar functions
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('open');
}

function showSection(section, event) {
    // Update active link
    if (event) {
        document.querySelectorAll('.sidebar-link').forEach(link => {
            link.classList.remove('active');
        });
        const link = event.target.closest('.sidebar-link');
        if (link) {
            link.classList.add('active');
        }
    }
    
    // Future: Show different content sections
    // For now, all sections show the same dashboard view
    console.log('Showing section:', section);
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

// =============================================================================
// Memory Management
// =============================================================================

let allMemories = [];
let currentMemoryFilename = null;

// Load all memories
async function loadMemories() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/memories`, {
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
            },
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        allMemories = data.memories || [];
        
        // Update count
        document.getElementById('memoryCount').textContent = 
            `${allMemories.length} ${allMemories.length === 1 ? 'memory' : 'memories'}`;
        
        // Display memories
        displayMemories(allMemories);
    } catch (error) {
        console.error('Error loading memories:', error);
        document.getElementById('memoryCount').textContent = 'Error loading memories';
    }
}

// Display memories in grid
function displayMemories(memories) {
    const grid = document.getElementById('memoryGrid');
    
    if (memories.length === 0) {
        grid.innerHTML = `
            <div class="col-span-full text-center py-12 text-gray-500">
                <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-4 opacity-50"></i>
                <p>No memories yet. Create your first one!</p>
            </div>
        `;
        lucide.createIcons();
        return;
    }
    
    grid.innerHTML = memories.map(memory => `
        <div class="border rounded-lg p-4 hover:shadow-lg transition-shadow cursor-pointer" onclick="viewMemory('${memory.filename}')">
            <div class="flex items-start justify-between mb-2">
                <h3 class="font-semibold text-gray-900 truncate flex-1">${escapeHtml(memory.title)}</h3>
                <span class="ml-2 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                    memory.type === 'long_term' ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'
                }">
                    ${memory.type.replace('_', ' ')}
                </span>
            </div>
            <p class="text-sm text-gray-600 line-clamp-3 mb-3">${escapeHtml(memory.content?.substring(0, 150) || '')}...</p>
            <div class="flex items-center justify-between text-xs text-gray-500">
                <span>${new Date(memory.created).toLocaleDateString()}</span>
                ${memory.tags && memory.tags.length > 0 ? `
                    <div class="flex gap-1">
                        ${memory.tags.slice(0, 2).map(tag => `
                            <span class="px-2 py-0.5 bg-gray-100 rounded">${escapeHtml(tag)}</span>
                        `).join('')}
                        ${memory.tags.length > 2 ? `<span class="px-2 py-0.5 bg-gray-100 rounded">+${memory.tags.length - 2}</span>` : ''}
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    lucide.createIcons();
}

// Search memories
function searchMemories() {
    const searchTerm = document.getElementById('memorySearch').value.toLowerCase();
    const typeFilter = document.getElementById('memoryTypeFilter').value;
    
    let filtered = allMemories;
    
    // Apply type filter
    if (typeFilter) {
        filtered = filtered.filter(m => m.type === typeFilter);
    }
    
    // Apply search
    if (searchTerm) {
        filtered = filtered.filter(m => 
            m.title.toLowerCase().includes(searchTerm) ||
            (m.content && m.content.toLowerCase().includes(searchTerm)) ||
            (m.tags && m.tags.some(tag => tag.toLowerCase().includes(searchTerm)))
        );
    }
    
    displayMemories(filtered);
}

// Filter memories by type
function filterMemories() {
    searchMemories(); // Reuse search function
}

// View memory details
async function viewMemory(filename) {
    const memory = allMemories.find(m => m.filename === filename);
    if (!memory) return;
    
    currentMemoryFilename = filename;
    
    // Populate view modal
    document.getElementById('viewMemoryTitle').textContent = memory.title;
    document.getElementById('viewMemoryType').textContent = memory.type.replace('_', ' ');
    document.getElementById('viewMemoryDate').textContent = 
        `Created ${new Date(memory.created).toLocaleString()}`;
    
    // Type badge color
    const badge = document.getElementById('viewMemoryTypeBadge');
    if (memory.type === 'long_term') {
        badge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800';
    } else {
        badge.className = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800';
    }
    
    // Content
    document.getElementById('viewMemoryContent').textContent = memory.content || '';
    
    // Tags
    const tagsContainer = document.getElementById('viewMemoryTagsContainer');
    if (memory.tags && memory.tags.length > 0) {
        tagsContainer.innerHTML = memory.tags.map(tag => `
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 mr-2">
                ${escapeHtml(tag)}
            </span>
        `).join('');
    } else {
        tagsContainer.innerHTML = '';
    }
    
    // Show modal
    document.getElementById('viewMemoryModal').style.display = 'flex';
    lucide.createIcons();
}

// Show create memory modal
function showCreateMemoryModal() {
    document.getElementById('memoryModalTitle').textContent = 'Create Memory';
    document.getElementById('memoryFilename').value = '';
    document.getElementById('memoryTitle').value = '';
    document.getElementById('memoryContent').value = '';
    document.getElementById('memoryType').value = 'short_term';
    document.getElementById('memoryTags').value = '';
    document.getElementById('memoryModal').style.display = 'flex';
}

// Edit current memory
function editCurrentMemory() {
    const memory = allMemories.find(m => m.filename === currentMemoryFilename);
    if (!memory) return;
    
    // Hide view modal
    document.getElementById('viewMemoryModal').style.display = 'none';
    
    // Populate edit form
    document.getElementById('memoryModalTitle').textContent = 'Edit Memory';
    document.getElementById('memoryFilename').value = memory.filename;
    document.getElementById('memoryTitle').value = memory.title;
    document.getElementById('memoryContent').value = memory.content || '';
    document.getElementById('memoryType').value = memory.type;
    document.getElementById('memoryTags').value = memory.tags ? memory.tags.join(', ') : '';
    
    // Show edit modal
    document.getElementById('memoryModal').style.display = 'flex';
}

// Save memory (create or update)
async function saveMemory(event) {
    event.preventDefault();
    
    const filename = document.getElementById('memoryFilename').value;
    const title = document.getElementById('memoryTitle').value;
    const content = document.getElementById('memoryContent').value;
    const type = document.getElementById('memoryType').value;
    const tagsInput = document.getElementById('memoryTags').value;
    const tags = tagsInput ? tagsInput.split(',').map(t => t.trim()).filter(t => t) : [];
    
    try {
        const isEdit = !!filename;
        const url = isEdit 
            ? `${API_BASE_URL}/api/v1/memories/${filename}`
            : `${API_BASE_URL}/api/v1/memories`;
        
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title,
                content,
                type,
                tags,
            }),
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save memory');
        }
        
        // Close modal and reload
        hideMemoryModal();
        await loadMemories();
        
        // Show success message
        showToast(isEdit ? 'Memory updated!' : 'Memory created!');
    } catch (error) {
        alert('Error saving memory: ' + error.message);
        console.error(error);
    }
}

// Delete current memory
async function deleteCurrentMemory() {
    if (!currentMemoryFilename) return;
    
    if (!confirm('Are you sure you want to delete this memory? This cannot be undone.')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/memories/${currentMemoryFilename}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${currentApiKey}`,
            },
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete memory');
        }
        
        // Close modal and reload
        hideViewMemoryModal();
        await loadMemories();
        
        showToast('Memory deleted');
    } catch (error) {
        alert('Error deleting memory: ' + error.message);
        console.error(error);
    }
}

// Hide modals
function hideMemoryModal() {
    document.getElementById('memoryModal').style.display = 'none';
}

function hideViewMemoryModal() {
    document.getElementById('viewMemoryModal').style.display = 'none';
    currentMemoryFilename = null;
}

// Utility: Show toast notification
function showToast(message) {
    // Simple toast - you can enhance this
    const toast = document.createElement('div');
    toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg z-50';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// Utility: Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Usage Chart
let usageChartInstance = null;
let currentChartDays = 7;

async function loadUsageChart(days = 7) {
    currentChartDays = days;
    
    // Update button states
    document.getElementById('chart7d').className = days === 7 
        ? 'px-3 py-1 text-sm rounded-md bg-purple-100 accent-lavender font-medium'
        : 'px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-100';
    document.getElementById('chart30d').className = days === 30
        ? 'px-3 py-1 text-sm rounded-md bg-purple-100 accent-lavender font-medium'
        : 'px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-100';
    
    // Show loading state
    document.getElementById('chartLoading').style.display = 'flex';
    
    try {
        // Generate mock data for now (replace with real API call)
        const labels = [];
        const data = [];
        const today = new Date();
        
        for (let i = days - 1; i >= 0; i--) {
            const date = new Date(today);
            date.setDate(date.getDate() - i);
            labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
            // Mock data - replace with actual API call
            data.push(Math.floor(Math.random() * 50) + 10);
        }
        
        // Destroy existing chart
        if (usageChartInstance) {
            usageChartInstance.destroy();
        }
        
        // Create new chart
        const ctx = document.getElementById('usageChart').getContext('2d');
        usageChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'API Requests',
                    data: data,
                    borderColor: 'rgb(124, 58, 237)',  // Lavender
                    backgroundColor: 'rgba(167, 139, 250, 0.2)',  // Light lavender fill
                    tension: 0.4,
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error loading chart:', error);
    } finally {
        document.getElementById('chartLoading').style.display = 'none';
    }
}

// Check if user should see upgrade banner
function checkUpgradeBanner(account, usage) {
    const banner = document.getElementById('upgradeBanner');
    const message = document.getElementById('upgradeMessage');
    
    // Show banner if free tier and using > 70% of any quota
    if (account.plan_tier === 'free') {
        const maxUsage = Math.max(
            usage.usage_percent.requests_today,
            usage.usage_percent.requests_month,
            usage.usage_percent.memories,
            usage.usage_percent.storage
        );
        
        if (maxUsage >= 70) {
            banner.style.display = 'block';
            
            if (maxUsage >= 90) {
                message.textContent = `You're at ${Math.round(maxUsage)}% of your free tier limits. Upgrade to continue.`;
            } else if (maxUsage >= 80) {
                message.textContent = `You're using ${Math.round(maxUsage)}% of your free tier quota. Consider upgrading.`;
            } else {
                message.textContent = `You're using ${Math.round(maxUsage)}% of your free tier. Unlock more with Pro!`;
            }
        }
    }
}
