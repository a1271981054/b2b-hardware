(() => {
  const body = document.body;
  const root = document.documentElement;

  const readTheme = () => {
    try {
      return localStorage.getItem('b-hardware-docs-theme');
    } catch {
      return null;
    }
  };

  const writeTheme = (theme) => {
    root.dataset.theme = theme;
    try {
      localStorage.setItem('b-hardware-docs-theme', theme);
    } catch {
      // Opening the generated pages from file:// can disable storage. Theme
      // switching still works for the current page in that case.
    }
  };

  writeTheme(readTheme() || 'light');

  document.querySelector('[data-theme-toggle]')?.addEventListener('click', () => {
    writeTheme(root.dataset.theme === 'dark' ? 'light' : 'dark');
  });

  document.querySelector('[data-sidebar-open]')?.addEventListener('click', () => {
    body.classList.add('sidebar-open');
  });

  document.querySelectorAll('[data-sidebar-close]').forEach((element) => {
    element.addEventListener('click', () => body.classList.remove('sidebar-open'));
  });

  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', () => body.classList.remove('sidebar-open'));
  });

  const search = document.querySelector('[data-doc-search]');
  const navLinks = [...document.querySelectorAll('[data-nav-link]')];
  const groups = [...document.querySelectorAll('.nav-group')];
  search?.addEventListener('input', () => {
    const query = search.value.trim().toLowerCase();
    navLinks.forEach((link) => {
      const match = !query || link.textContent.toLowerCase().includes(query);
      link.hidden = !match;
    });
    groups.forEach((group) => {
      group.hidden = ![...group.querySelectorAll('[data-nav-link]')].some((link) => !link.hidden);
    });
  });

  document.addEventListener('keydown', (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      search?.focus();
    }
    if (event.key === 'Escape') {
      body.classList.remove('sidebar-open');
      if (search) {
        search.value = '';
        search.dispatchEvent(new Event('input'));
        search.blur();
      }
    }
  });

  document.querySelectorAll('[data-copy-code]').forEach((button) => {
    button.addEventListener('click', async () => {
      const text = button.dataset.copyCode || '';
      try {
        await navigator.clipboard.writeText(text);
        button.textContent = '已复制';
      } catch {
        button.textContent = '请手动复制';
      }
      window.setTimeout(() => {
        button.textContent = '复制';
      }, 1600);
    });
  });

  const tocLinks = [...document.querySelectorAll('.toc-link')];
  if (tocLinks.length && 'IntersectionObserver' in window) {
    const headings = tocLinks
      .map((link) => document.getElementById(link.getAttribute('href')?.slice(1)))
      .filter(Boolean);
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        tocLinks.forEach((link) => link.classList.toggle('active', link.getAttribute('href') === `#${entry.target.id}`));
      });
    }, { rootMargin: '-90px 0px -65% 0px', threshold: 0 });
    headings.forEach((heading) => observer.observe(heading));
  }
})();
