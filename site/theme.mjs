const storageKey = 'sqltoviz-theme';

export function initializeTheme(button) {
  const preference = window.matchMedia('(prefers-color-scheme: light)');
  let saved;
  try {
    saved = window.localStorage.getItem(storageKey);
  } catch {
    // The system preference still works if storage is unavailable.
  }
  let override = saved === 'light' || saved === 'dark' ? saved : null;

  function render() {
    const light = override === null ? preference.matches : override === 'light';
    document.body.classList.toggle('light', light);
    button.setAttribute('aria-pressed', String(light));
  }

  preference.addEventListener('change', render);
  button.addEventListener('click', () => {
    override = document.body.classList.contains('light') ? 'dark' : 'light';
    try {
      window.localStorage.setItem(storageKey, override);
    } catch {
      // The current tab still retains the user's choice.
    }
    render();
  });
  render();

  return {
    setLanguage(language) {
      button.setAttribute('aria-label', language === 'es' ? 'Modo claro' : 'Light mode');
    },
  };
}
