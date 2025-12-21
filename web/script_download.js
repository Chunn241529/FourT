document.addEventListener('DOMContentLoaded', () => {
    // GitHub Repo - for release info only
    const GITHUB_REPO = 'Chunn241529/FourT';
    // API base URL for our stats
    const API_BASE = window.location.origin;

    // Generate particles
    const particlesContainer = document.getElementById('particles');
    if (particlesContainer) {
        const particleCount = 20;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.classList.add('particle');

            const left = Math.random() * 100;
            const duration = 10 + Math.random() * 20;
            const delay = Math.random() * 5;
            const size = 2 + Math.random() * 4;

            particle.style.left = `${left}%`;
            particle.style.setProperty('--duration', `${duration}s`);
            particle.style.animationDelay = `${delay}s`;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;

            particlesContainer.appendChild(particle);
        }
    }

    // Parallax effect for orbs
    document.addEventListener('mousemove', (e) => {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;

        const orbs = document.querySelectorAll('.gradient-orb');
        orbs.forEach((orb, index) => {
            const speed = (index + 1) * 20;
            const xOffset = (0.5 - x) * speed;
            const yOffset = (0.5 - y) * speed;

            orb.style.transform = `translate(${xOffset}px, ${yOffset}px)`;
        });
    });

    // DOM Elements
    const releasesContent = document.getElementById('releasesContent');
    const totalDownloadsEl = document.getElementById('totalDownloads');

    // Store our download stats
    let downloadStats = { total_downloads: 0, assets: {} };
    // Store releases for re-rendering
    let cachedReleases = [];

    // Auto-fetch on load - stats first, then releases
    init();

    async function init() {
        await fetchDownloadStats();
        await fetchReleases();
    }

    // Fetch our download stats from backend
    async function fetchDownloadStats() {
        try {
            const response = await fetch(`${API_BASE}/api/stats/downloads`);
            if (response.ok) {
                downloadStats = await response.json();
                updateTotalDownloadsDisplay();
                // Re-render releases if already loaded
                if (cachedReleases.length > 0) {
                    renderReleases(cachedReleases);
                }
            }
        } catch (error) {
            console.error('Failed to fetch download stats:', error);
        }
    }

    // Update total downloads display
    function updateTotalDownloadsDisplay() {
        totalDownloadsEl.querySelector('span').textContent = downloadStats.total_downloads.toLocaleString();
    }

    // Fetch releases from GitHub API
    async function fetchReleases() {
        showLoading();

        try {
            const response = await fetch(`https://api.github.com/repos/${GITHUB_REPO}/releases`);

            if (!response.ok) {
                throw new Error(`Failed to fetch releases (${response.status})`);
            }

            const releases = await response.json();

            if (releases.length === 0) {
                showEmpty('No releases found for this repository.');
                return;
            }

            // Cache releases for re-rendering when stats update
            cachedReleases = releases;
            renderReleases(releases);
        } catch (error) {
            showError(error.message);
        }
    }

    // Render releases table
    function renderReleases(releases) {
        const now = new Date();

        // Build HTML
        let html = '';

        releases.forEach((release, index) => {
            const releaseDate = new Date(release.published_at);
            const activeDays = Math.floor((now - releaseDate) / (1000 * 60 * 60 * 24));
            const formattedDate = releaseDate.toISOString().split('T')[0];

            // Get download count from our stats
            let releaseDownloads = 0;
            release.assets.forEach(asset => {
                releaseDownloads += (downloadStats.assets[asset.name]?.count || 0);
            });

            // Determine badge
            let badge = '';
            if (index === 0) {
                badge = '<span class="release-badge badge-latest">Latest</span>';
            } else if (release.prerelease) {
                badge = '<span class="release-badge badge-prerelease">Pre-release</span>';
            }

            html += `
                <div class="release-row" data-index="${index}">
                    <div class="release-name">
                        <span class="expand-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                            </svg>
                        </span>
                        <span class="release-version">FourT v${release.tag_name}</span>
                        ${badge}
                    </div>
                    <div class="release-date">${formattedDate}</div>
                    <div class="active-days">${activeDays.toFixed(1)}</div>
                    <div class="download-count" data-release="${index}">${releaseDownloads.toLocaleString()}</div>
                </div>
                <div class="assets-container" data-index="${index}">
                    ${renderAssets(release.assets, index)}
                </div>
            `;
        });

        releasesContent.innerHTML = html;

        // Add click listeners for expanding rows
        document.querySelectorAll('.release-row').forEach(row => {
            row.addEventListener('click', () => {
                row.classList.toggle('expanded');
            });
        });
    }

    // Render assets for a release
    function renderAssets(assets, releaseIndex) {
        if (assets.length === 0) {
            return '<div class="asset-item"><span style="color: rgba(255,255,255,0.4);">No downloadable assets</span></div>';
        }

        return assets.map(asset => {
            const sizeInMB = (asset.size / (1024 * 1024)).toFixed(2);
            const assetCount = downloadStats.assets[asset.name]?.count || 0;
            return `
                <div class="asset-item">
                    <div class="asset-info">
                        <div class="asset-icon">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                        </div>
                        <div>
                            <div class="asset-name">${asset.name}</div>
                            <div class="asset-size">${sizeInMB} MB</div>
                        </div>
                    </div>
                    <div class="asset-downloads">
                        <span class="asset-download-count" data-asset="${asset.name}">${assetCount.toLocaleString()} downloads</span>
                        <a href="${asset.browser_download_url}" class="asset-download-btn" target="_blank" data-asset="${asset.name}" data-release="${releaseIndex}" onclick="incrementDownload(event, this)">
                            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Download
                        </a>
                    </div>
                </div>
            `;
        }).join('');
    }

    // Increment download count when clicked
    window.incrementDownload = async function (event, btn) {
        const assetName = btn.getAttribute('data-asset');
        const releaseIndex = btn.getAttribute('data-release');

        // Optimistic update - update UI immediately
        const countEl = document.querySelector(`.asset-download-count[data-asset="${assetName}"]`);
        if (countEl) {
            const currentCount = parseInt(countEl.textContent.replace(/[^0-9]/g, '')) || 0;
            countEl.textContent = (currentCount + 1).toLocaleString() + ' downloads';
        }

        // Update release total
        const releaseCountEl = document.querySelector(`.download-count[data-release="${releaseIndex}"]`);
        if (releaseCountEl) {
            const currentCount = parseInt(releaseCountEl.textContent.replace(/[^0-9]/g, '')) || 0;
            releaseCountEl.textContent = (currentCount + 1).toLocaleString();
        }

        // Update total downloads
        const totalSpan = totalDownloadsEl.querySelector('span');
        const totalCount = parseInt(totalSpan.textContent.replace(/[^0-9]/g, '')) || 0;
        totalSpan.textContent = (totalCount + 1).toLocaleString();

        // Call API to persist the count
        try {
            await fetch(`${API_BASE}/api/stats/downloads/increment?asset_name=${encodeURIComponent(assetName)}`, {
                method: 'POST'
            });
        } catch (error) {
            console.error('Failed to increment download count:', error);
        }
    };

    // Show loading state
    function showLoading() {
        releasesContent.innerHTML = `
            <div class="loading-container">
                <div class="loading-spinner"></div>
                <span>Loading releases...</span>
            </div>
        `;
    }

    // Show error state
    function showError(message) {
        releasesContent.innerHTML = `
            <div class="error-container">
                <svg class="error-icon" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <div>${message}</div>
            </div>
        `;
    }

    // Show empty state
    function showEmpty(message) {
        releasesContent.innerHTML = `
            <div class="empty-state">${message}</div>
        `;
    }
});
