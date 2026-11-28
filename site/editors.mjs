export function initializeEditors({ sql, rows, format, status, analyze }) {
  let spanish = false;

  for (const editor of [sql, rows]) {
    editor.addEventListener('keydown', event => {
      if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        analyze();
      }
    });
  }

  rows.addEventListener('input', () => { status.textContent = ''; });
  format.addEventListener('click', () => {
    try {
      rows.value = JSON.stringify(JSON.parse(rows.value), null, 2);
      status.textContent = spanish ? 'JSON formateado.' : 'JSON formatted.';
    } catch {
      status.textContent = spanish ? 'No se pudo formatear el JSON. Revisa la sintaxis.' : 'Unable to format JSON. Check its syntax.';
    }
  });

  return {
    setLanguage(language) {
      spanish = language === 'es';
      format.textContent = spanish ? 'Formatear JSON' : 'Format JSON';
      status.textContent = '';
    },
  };
}
