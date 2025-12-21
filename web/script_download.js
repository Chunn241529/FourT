document.addEventListener('DOMContentLoaded', () => {
    // GitHub Repo - hardcoded
    const GITHUB_REPO = 'Chunn241529/FourT';

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

    // Auto-fetch on load
    fetchReleases();

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

            renderReleases(releases);
        } catch (error) {
            showError(error.message);
        }
    }

    // Render releases table
    function renderReleases(releases) {
        let totalDownloads = 0;
        const now = new Date();

        // Calculate total downloads
        releases.forEach(release => {
            release.assets.forEach(asset => {
                totalDownloads += asset.download_count;
            });
        });

        // Update total downloads display
        totalDownloadsEl.querySelector('span').textContent = totalDownloads.toLocaleString();

        // Build HTML
        let html = '';

        releases.forEach((release, index) => {
            const releaseDate = new Date(release.published_at);
            const activeDays = Math.floor((now - releaseDate) / (1000 * 60 * 60 * 24));
            const formattedDate = releaseDate.toISOString().split('T')[0];

            // Calculate release download count
            let releaseDownloads = 0;
            release.assets.forEach(asset => {
                releaseDownloads += asset.download_count;
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
                    <div class="download-count">${releaseDownloads.toLocaleString()}</div>
                </div>
                <div class="assets-container" data-index="${index}">
                    ${renderAssets(release.assets)}
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
    function renderAssets(assets) {
        if (assets.length === 0) {
            return '<div class="asset-item"><span style="color: rgba(255,255,255,0.4);">No downloadable assets</span></div>';
        }

        return assets.map(asset => {
            const sizeInMB = (asset.size / (1024 * 1024)).toFixed(2);
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
                        <span class="asset-download-count">${asset.download_count.toLocaleString()} downloads</span>
                        <a href="${asset.browser_download_url}" class="asset-download-btn" target="_blank">
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
