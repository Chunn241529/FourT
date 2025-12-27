/**
 * FourT MIDI Community - Frontend JavaScript
 */

// API Base URL
const API_BASE = '/api';

// State
let currentUser = null;
let accessToken = localStorage.getItem('access_token');
let refreshToken = localStorage.getItem('refresh_token');
let currentPage = 1;
let currentSort = 'newest';
let currentSearch = '';

// MIDI Player State
let currentlyPlayingId = null;
let currentlyPlayingTitle = '';
let isPlaying = false;

// ============== Initialization ==============

document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    // Only load MIDI list if on the community index page (has midi-grid)
    if (document.getElementById('midi-grid')) {
        loadMidiList();
    }
    setupEventListeners();
});

function setupEventListeners() {
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            currentSort = tab.dataset.sort;
            currentPage = 1;
            loadMidiList();
        });
    });

    // Search on Enter
    document.getElementById('search-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchMidi();
    });

    // Close user menu on click outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.nav-user')) {
            document.getElementById('user-menu')?.classList.remove('active');
        }
    });
}

// ============== Auth Functions ==============

async function checkAuth() {
    if (!accessToken) {
        updateAuthUI(null);
        return;
    }

    try {
        const response = await fetchWithAuth('/auth/me');
        if (response.ok) {
            currentUser = await response.json();
            updateAuthUI(currentUser);
        } else {
            // Try refresh token
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                checkAuth();
            } else {
                logout();
            }
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        updateAuthUI(null);
    }
}

async function refreshAccessToken() {
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('refresh_token', refreshToken);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }
    return false;
}

function updateAuthUI(user) {
    const authDiv = document.getElementById('nav-auth');
    const userDiv = document.getElementById('nav-user');

    if (user) {
        if (authDiv) authDiv.style.display = 'none';
        if (userDiv) {
            userDiv.style.display = 'flex';
            const pointsEl = document.getElementById('user-points');
            const initialEl = document.getElementById('user-initial');
            if (pointsEl) pointsEl.textContent = `💰 ${user.points} pts`;
            if (initialEl) initialEl.textContent = user.username[0].toUpperCase();
        }
    } else {
        if (authDiv) authDiv.style.display = 'flex';
        if (userDiv) userDiv.style.display = 'none';
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            accessToken = data.access_token;
            refreshToken = data.refresh_token;
            currentUser = data.user;
            localStorage.setItem('access_token', accessToken);
            localStorage.setItem('refresh_token', refreshToken);
            updateAuthUI(currentUser);
            closeModals();
            showToast('Đăng nhập thành công!', 'success');
        } else {
            const error = await response.json();
            showToast(error.detail || 'Đăng nhập thất bại', 'error');
        }
    } catch (error) {
        showToast('Lỗi kết nối server', 'error');
    }
}

async function handleRegister(e) {
    e.preventDefault();
    const username = document.getElementById('register-username').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;

    try {
        const response = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, email, password })
        });

        if (response.ok) {
            closeModals();
            showToast('Đăng ký thành công! +5 điểm 🎉', 'success');
            showLoginModal();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Đăng ký thất bại', 'error');
        }
    } catch (error) {
        showToast('Lỗi kết nối server', 'error');
    }
}

function logout() {
    accessToken = null;
    refreshToken = null;
    currentUser = null;
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    updateAuthUI(null);
    showToast('Đã đăng xuất', 'info');
}

function toggleUserMenu() {
    document.getElementById('user-menu')?.classList.toggle('active');
}

// ============== MIDI Functions ==============

async function loadMidiList() {
    const grid = document.getElementById('midi-grid');
    if (!grid) return; // Guard for pages without midi-grid

    grid.innerHTML = '<div class="loading-spinner"><div class="spinner"></div><p>Đang tải...</p></div>';

    try {
        const params = new URLSearchParams({
            page: currentPage,
            page_size: 12,
            sort: currentSort
        });
        if (currentSearch) params.append('search', currentSearch);

        const response = await fetch(`${API_BASE}/community/midi?${params}`);
        const data = await response.json();

        if (data.items.length === 0) {
            grid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🎵</div>
                    <h3>Chưa có MIDI nào</h3>
                    <p>Hãy là người đầu tiên upload MIDI!</p>
                </div>
            `;
        } else {
            grid.innerHTML = data.items.map(midi => createMidiCard(midi)).join('');
        }

        renderPagination(data.total, data.page, data.page_size);
    } catch (error) {
        console.error('Failed to load MIDI list:', error);
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <h3>Lỗi tải dữ liệu</h3>
                <p>Vui lòng thử lại sau</p>
            </div>
        `;
    }
}

function createMidiCard(midi) {
    const typeClass = midi.midi_type || 'normal';
    const cost = getDownloadCost(currentUser?.rank || 'newcomer', typeClass);

    return `
        <div class="midi-card" onclick="showMidiDetail(${midi.id})">
            <div class="midi-card-header">
                <div class="midi-card-icon">🎵</div>
                <span class="midi-type-badge ${typeClass}">${typeClass}</span>
            </div>
            <h3 class="midi-card-title">${escapeHtml(midi.title)}</h3>
            <p class="midi-card-uploader">bởi ${escapeHtml(midi.uploader_username || 'Unknown')}</p>
            <div class="midi-card-stats">
                <div class="midi-stat">
                    ⭐ <span class="midi-stat-value">${midi.avg_rating?.toFixed(1) || '0.0'}</span>
                </div>
                <div class="midi-stat">
                    ⬇️ <span class="midi-stat-value">${formatNumber(midi.download_count)}</span>
                </div>
            </div>
            <div class="midi-card-footer">
                <span class="midi-cost">${cost === 0 ? '🆓 Miễn phí' : `💰 ${cost} pts`}</span>
                <button class="btn btn-primary btn-sm" onclick="event.stopPropagation(); downloadMidi(${midi.id})">
                    Tải xuống
                </button>
            </div>
        </div>
    `;
}

function getDownloadCost(rank, midiType) {
    const baseCosts = { normal: 3, premium: 8, exclusive: 15 };
    const discounts = { newcomer: 0, player: 1, contributor: 1, artist: 2, star: 3, legend: 99 };
    const base = baseCosts[midiType] || 3;
    const discount = discounts[rank] || 0;
    return Math.max(0, base - discount);
}

async function showMidiDetail(midiId) {
    const modal = document.getElementById('midi-modal');
    const content = document.getElementById('midi-detail-content');
    content.innerHTML = '<div class="loading-spinner"><div class="spinner"></div></div>';
    modal.classList.add('active');

    try {
        const [midiRes, commentsRes] = await Promise.all([
            fetch(`${API_BASE}/community/midi/${midiId}`),
            fetch(`${API_BASE}/community/midi/${midiId}/comments`)
        ]);

        const midi = await midiRes.json();
        const comments = await commentsRes.json();

        content.innerHTML = `
            <div class="midi-detail">
                <div class="midi-detail-header">
                    <div class="midi-detail-icon">🎵</div>
                    <div class="midi-detail-info">
                        <h2>${escapeHtml(midi.title)}</h2>
                        <div class="midi-detail-meta">
                            <span>👤 ${escapeHtml(midi.uploader_username || 'Unknown')}</span>
                            <span>📁 ${formatBytes(midi.file_size)}</span>
                            ${midi.duration_seconds ? `<span>⏱️ ${formatDuration(midi.duration_seconds)}</span>` : ''}
                        </div>
                    </div>
                </div>
                
                <div class="midi-detail-stats">
                    <div class="detail-stat">
                        <div class="detail-stat-value">⭐ ${midi.avg_rating?.toFixed(1) || '0.0'}</div>
                        <div class="detail-stat-label">${midi.rating_count} đánh giá</div>
                    </div>
                    <div class="detail-stat">
                        <div class="detail-stat-value">⬇️ ${formatNumber(midi.download_count)}</div>
                        <div class="detail-stat-label">Lượt tải</div>
                    </div>
                </div>

                <div class="midi-detail-actions">
                    <button class="btn btn-outline midi-preview-btn" id="detail-play-btn" 
                            onclick="playMidi(${midi.id}, '${escapeHtml(midi.title).replace(/'/g, "\\'")}')">
                        ${currentlyPlayingId === midi.id && isPlaying ? '⏸️' : '▶️'}
                    </button>
                    <button class="btn btn-primary" onclick="downloadMidi(${midi.id})">
                        💾 Tải xuống (${getDownloadCost(currentUser?.rank || 'newcomer', midi.midi_type)} pts)
                    </button>
                    ${currentUser ? `
                        <div class="rating-stars" id="rating-stars">
                            ${[1, 2, 3, 4, 5].map(i => `<span class="star" data-rating="${i}" onclick="rateMidi(${midi.id}, ${i})">★</span>`).join('')}
                        </div>
                    ` : ''}
                </div>

                ${midi.description ? `
                    <div class="midi-detail-description">
                        <strong>Mô tả:</strong><br>
                        ${escapeHtml(midi.description)}
                    </div>
                ` : ''}

                <div class="comments-section">
                    <h3>💬 Bình luận (${comments.length})</h3>
                    ${currentUser ? `
                        <form class="comment-form" onsubmit="addComment(event, ${midi.id})">
                            <input type="text" id="new-comment" placeholder="Viết bình luận..." required>
                            <button class="btn btn-primary">Gửi</button>
                        </form>
                    ` : '<p style="color: var(--text-secondary); margin-bottom: 16px;">Đăng nhập để bình luận</p>'}
                    <div class="comment-list" id="comment-list">
                        ${comments.map(c => `
                            <div class="comment">
                                <div class="comment-header">
                                    <span class="comment-author">${escapeHtml(c.username)}</span>
                                    <span class="comment-time">${formatDate(c.created_at)}</span>
                                </div>
                                <p class="comment-content">${escapeHtml(c.content)}</p>
                            </div>
                        `).join('') || '<p style="color: var(--text-secondary);">Chưa có bình luận nào</p>'}
                    </div>
                </div>
            </div>
        `;

        // Load user's existing rating and highlight stars
        if (currentUser) {
            try {
                const ratingRes = await fetchWithAuth(`/community/midi/${midiId}/my-rating`);
                if (ratingRes.ok) {
                    const ratingData = await ratingRes.json();
                    if (ratingData.stars > 0) {
                        document.querySelectorAll('#rating-stars .star').forEach((star, i) => {
                            star.classList.toggle('active', i < ratingData.stars);
                        });
                    }
                }
            } catch (e) {
                console.error('Failed to load user rating:', e);
            }
        }
    } catch (error) {
        console.error('Failed to load MIDI detail:', error);
        content.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">Lỗi tải dữ liệu</p>';
    }
}

async function downloadMidi(midiId) {
    if (!currentUser) {
        showToast('Vui lòng đăng nhập để tải MIDI', 'info');
        showLoginModal();
        return;
    }

    try {
        const response = await fetchWithAuth(`/community/midi/${midiId}/download`, { method: 'POST' });
        const data = await response.json();

        if (response.ok) {
            showToast(data.message, 'success');

            // Fetch file with auth token and trigger download
            const fileResponse = await fetchWithAuth(data.file_path);
            if (fileResponse.ok) {
                const blob = await fileResponse.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `midi_${midiId}.mid`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                showToast('Không thể tải file', 'error');
            }

            // Update user points
            checkAuth();
        } else {
            showToast(data.detail || 'Tải xuống thất bại', 'error');
        }
    } catch (error) {
        console.error('Download error:', error);
        showToast('Lỗi kết nối server', 'error');
    }
}

async function rateMidi(midiId, stars) {
    if (!currentUser) {
        showToast('Vui lòng đăng nhập để đánh giá', 'info');
        return;
    }

    try {
        const response = await fetchWithAuth(`/community/midi/${midiId}/rate`, {
            method: 'POST',
            body: JSON.stringify({ stars })
        });

        if (response.ok) {
            const data = await response.json();
            showToast(`Đã đánh giá ${stars} sao!`, 'success');
            // Update stars UI
            document.querySelectorAll('#rating-stars .star').forEach((star, i) => {
                star.classList.toggle('active', i < stars);
            });
        } else {
            const error = await response.json();
            showToast(error.detail || 'Đánh giá thất bại', 'error');
        }
    } catch (error) {
        showToast('Lỗi kết nối server', 'error');
    }
}

async function addComment(e, midiId) {
    e.preventDefault();
    const input = document.getElementById('new-comment');
    const content = input.value.trim();
    if (!content) return;

    try {
        const response = await fetchWithAuth(`/community/midi/${midiId}/comments`, {
            method: 'POST',
            body: JSON.stringify({ content })
        });

        if (response.ok) {
            const comment = await response.json();
            const list = document.getElementById('comment-list');
            list.insertAdjacentHTML('afterbegin', `
                <div class="comment">
                    <div class="comment-header">
                        <span class="comment-author">${escapeHtml(comment.username)}</span>
                        <span class="comment-time">Vừa xong</span>
                    </div>
                    <p class="comment-content">${escapeHtml(comment.content)}</p>
                </div>
            `);
            input.value = '';
            showToast('Bình luận đã được gửi! +1 điểm', 'success');
            checkAuth();
        } else {
            const error = await response.json();
            showToast(error.detail || 'Gửi bình luận thất bại', 'error');
        }
    } catch (error) {
        showToast('Lỗi kết nối server', 'error');
    }
}

function searchMidi() {
    currentSearch = document.getElementById('search-input').value.trim();
    currentPage = 1;
    loadMidiList();
}

// ============== UI Helpers ==============

function renderPagination(total, page, pageSize) {
    const totalPages = Math.ceil(total / pageSize);
    const pagination = document.getElementById('pagination');

    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let html = '';
    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }
    pagination.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    loadMidiList();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showLoginModal() {
    closeModals();
    document.getElementById('login-modal').classList.add('active');
}

function showRegisterModal() {
    closeModals();
    document.getElementById('register-modal').classList.add('active');
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `${getToastIcon(type)} ${message}`;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function getToastIcon(type) {
    const icons = { success: '✅', error: '❌', info: 'ℹ️' };
    return icons[type] || 'ℹ️';
}

// ============== Utility Functions ==============

async function fetchWithAuth(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {})
    };

    if (accessToken) {
        headers['Authorization'] = `Bearer ${accessToken}`;
    }

    return fetch(API_BASE + url, { ...options, headers });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatNumber(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num?.toString() || '0';
}

function formatBytes(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Vừa xong';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' phút trước';
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' giờ trước';
    if (diff < 604800000) return Math.floor(diff / 86400000) + ' ngày trước';

    return date.toLocaleDateString('vi-VN');
}

// ============== MIDI Player Functions ==============

/**
 * Play a MIDI file from the community
 * @param {number} midiId - ID of the MIDI file
 * @param {string} title - Title of the MIDI file
 */
function playMidi(midiId, title) {
    // If same MIDI is playing, toggle pause/play
    if (currentlyPlayingId === midiId && isPlaying) {
        stopMidi();
        return;
    }

    // Stop any currently playing MIDI
    if (isPlaying) {
        MIDIjs.stop();
    }

    // Update state
    currentlyPlayingId = midiId;
    currentlyPlayingTitle = title;
    isPlaying = true;

    // Build preview URL
    const previewUrl = `${API_BASE}/community/midi/${midiId}/preview`;

    // Play using MIDIjs
    try {
        MIDIjs.play(previewUrl);

        // Listen for when playback ends
        MIDIjs.message_callback = function (message) {
            if (message && message.includes && message.includes('ended')) {
                onMidiEnded();
            }
        };

        updatePlayerUI();
        showToast(`🎵 Đang phát: ${title}`, 'success');
    } catch (error) {
        console.error('MIDI playback error:', error);
        showToast('Không thể phát MIDI', 'error');
        resetPlayerState();
    }
}

/**
 * Stop MIDI playback
 */
function stopMidi() {
    if (typeof MIDIjs !== 'undefined') {
        MIDIjs.stop();
    }
    resetPlayerState();
    updatePlayerUI();
}

/**
 * Toggle play/pause for current MIDI
 */
function togglePlay() {
    if (!currentlyPlayingId) return;

    if (isPlaying) {
        stopMidi();
    } else {
        playMidi(currentlyPlayingId, currentlyPlayingTitle);
    }
}

/**
 * Called when MIDI playback ends naturally
 */
function onMidiEnded() {
    resetPlayerState();
    updatePlayerUI();
}

/**
 * Reset player state
 */
function resetPlayerState() {
    isPlaying = false;
    // Keep currentlyPlayingId and title for "resume" capability
}

/**
 * Update player UI elements
 */
function updatePlayerUI() {
    const playerBar = document.getElementById('midi-player-bar');
    const playerTitle = document.getElementById('player-title');
    const playerPlayBtn = document.getElementById('player-play-btn');
    const playerStatus = document.getElementById('player-status');
    const detailPlayBtn = document.getElementById('detail-play-btn');

    if (!playerBar) return;

    // Update player bar visibility and state
    if (currentlyPlayingId) {
        playerBar.classList.add('active');
        document.body.classList.add('player-active');
        playerPlayBtn.disabled = false;
        playerTitle.textContent = currentlyPlayingTitle || 'Unknown';
    } else {
        // Keep bar visible if we have a recent track
        playerTitle.textContent = 'Chọn bài để nghe thử';
        playerPlayBtn.disabled = true;
    }

    // Update play/pause state
    if (isPlaying) {
        playerBar.classList.add('playing');
        playerPlayBtn.textContent = '⏸️';
        playerStatus.textContent = '🎵';
    } else {
        playerBar.classList.remove('playing');
        playerPlayBtn.textContent = '▶️';
        playerStatus.textContent = '🎵';
    }

    // Update detail modal play button if visible
    if (detailPlayBtn) {
        if (isPlaying) {
            detailPlayBtn.textContent = '⏸️';
            detailPlayBtn.classList.add('playing');
        } else {
            detailPlayBtn.textContent = '▶️';
            detailPlayBtn.classList.remove('playing');
        }
    }
}

// Check if MIDIjs is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (typeof MIDIjs === 'undefined') {
        console.warn('MIDIjs not loaded. MIDI playback will not work.');
    }
});
