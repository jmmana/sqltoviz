import { COLUMN_FEATURES, GLOBAL_FEATURES, SQL_FEATURES } from './sdk/contract.js';

export function createTensorInspector(result, columns, spanish) {
  const tableFeatures = [...SQL_FEATURES, ...GLOBAL_FEATURES].map(([name]) => name);
  const columnFeatures = COLUMN_FEATURES.map(([name]) => name);
  const tensors = {
    contract_version: result.contract_version,
    contract_sha256: result.contract_sha256,
    model_status: result.model_status,
    table: {
      shape: [1, tableFeatures.length],
      features: tableFeatures,
      values: [Array.from(result.table_features)],
    },
    columns: {
      shape: [columns.length, columnFeatures.length],
      features: columnFeatures,
      names: columns,
      values: result.column_features.map(values => Array.from(values)),
    },
  };

  const inspector = document.createElement('details');
  const title = document.createElement('summary');
  title.textContent = spanish ? 'Inspeccionar tensores' : 'Inspect tensors';
  const data = document.createElement('pre');
  data.textContent = JSON.stringify(tensors, null, 2);
  const download = document.createElement('button');
  download.type = 'button';
  download.textContent = spanish ? 'Descargar tensores JSON' : 'Download tensor JSON';
  download.addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([data.textContent], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'sqltoviz-tensors.json';
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  inspector.append(title, download, data);
  return inspector;
}
