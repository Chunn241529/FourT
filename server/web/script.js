document.addEventListener('DOMContentLoaded', () => {
    // Generate particles
    const particlesContainer = document.getElementById('particles');
    const particleCount = 20;

    for (let i = 0; i < particleCount; i++) {
        const particle = document.createElement('div');
        particle.classList.add('particle');

        // Random properties
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

    // Fetch and update user/download count
    async function fetchStats() {
        try {
            const userCountEl = document.getElementById('user-count');
            if (!userCountEl) return;

            const response = await fetch('/api/releases');
            if (response.ok) {
                const data = await response.json();
                const count = data.total_downloads ?? 0;

                // Format: K, M, B
                let formattedCount;
                if (count >= 1000000000) {
                    formattedCount = (count / 1000000000).toFixed(1) + 'B';
                } else if (count >= 1000000) {
                    formattedCount = (count / 1000000).toFixed(1) + 'M';
                } else if (count >= 1000) {
                    formattedCount = (count / 1000).toFixed(1) + 'K';
                } else {
                    formattedCount = count.toLocaleString();
                }

                // Remove .0 if present (e.g. 1.0K -> 1K)
                formattedCount = formattedCount.replace('.0', '');

                userCountEl.textContent = formattedCount;
            }
        } catch (error) {
            console.error('Failed to fetch stats:', error);
        }
    }

    fetchStats();
});
