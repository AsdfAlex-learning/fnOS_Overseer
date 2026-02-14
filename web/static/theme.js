(function(){
  const key = 'theme';

  function updateIcon(theme) {
    const btn = document.getElementById('theme-toggle');
    if (btn) {
      btn.textContent = theme === 'dark' ? '🌙' : '☀️';
    }
  }

  function apply(theme) {
    document.documentElement.classList.toggle('dark-mode', theme === 'dark');
    updateIcon(theme);
  }

  function detect() {
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }

  function init() {
    const saved = localStorage.getItem(key);
    const theme = saved ? saved : detect();

    if (document.readyState === 'loading') {
      window.addEventListener('DOMContentLoaded', () => apply(theme));
    } else {
      apply(theme);
    }
  }

  function toggle(event) {
    const isDark = document.documentElement.classList.contains('dark-mode');
    const next = isDark ? 'light' : 'dark';
    
    if (!document.startViewTransition) {
      localStorage.setItem(key, next);
      apply(next);
      return;
    }

    const x = event ? event.clientX : window.innerWidth / 2;
    const y = event ? event.clientY : window.innerHeight / 2;
    const endRadius = Math.hypot(
      Math.max(x, window.innerWidth - x),
      Math.max(y, window.innerHeight - y)
    );

    if (isDark) {
      document.documentElement.classList.add('transition-reverse');
    }

    const transition = document.startViewTransition(() => {
      localStorage.setItem(key, next);
      apply(next);
    });

    transition.ready.then(() => {
      const clipPath = [
        `circle(0px at ${x}px ${y}px)`,
        `circle(${endRadius}px at ${x}px ${y}px)`
      ];
      
      const isDarkToLight = isDark; 
      
      document.documentElement.animate(
        {
          clipPath: isDarkToLight ? [...clipPath].reverse() : clipPath,
        },
        {
          duration: 400,
          easing: 'ease-out',
          pseudoElement: isDarkToLight ? '::view-transition-old(root)' : '::view-transition-new(root)',
          fill: 'forwards',
        }
      );
    });

    transition.finished.then(() => {
      document.documentElement.classList.remove('transition-reverse');
    });
  }

  window.__themeToggle = (e) => toggle(e || window.event);
  init();
})();