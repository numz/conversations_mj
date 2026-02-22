/**
 * Table export utilities - CSV only (no external dependencies)
 */

// Types
interface TableData {
  headers: string[];
  rows: string[][];
}

/**
 * Parse HTML table element to extract data
 */
export function parseHtmlTable(tableElement: HTMLTableElement): TableData {
  const headers: string[] = [];
  const rows: string[][] = [];

  // Get headers from thead or first row
  const headerCells = tableElement.querySelectorAll('thead th, thead td');
  if (headerCells.length > 0) {
    headerCells.forEach((cell) => {
      headers.push(cell.textContent?.trim() || '');
    });
  }

  // Get body rows
  const bodyRows = tableElement.querySelectorAll('tbody tr');
  bodyRows.forEach((row) => {
    const cells = row.querySelectorAll('td, th');
    const rowData: string[] = [];
    cells.forEach((cell) => {
      rowData.push(cell.textContent?.trim() || '');
    });
    if (rowData.length > 0) {
      rows.push(rowData);
    }
  });

  // If no thead, use first row as headers
  if (headers.length === 0 && rows.length > 0) {
    const firstRow = tableElement.querySelector('tr');
    if (firstRow) {
      const cells = firstRow.querySelectorAll('td, th');
      cells.forEach((cell) => {
        headers.push(cell.textContent?.trim() || '');
      });
      // Remove first row from rows if it was used as headers
      if (rows[0]?.join('') === headers.join('')) {
        rows.shift();
      }
    }
  }

  return { headers, rows };
}

/**
 * Download helper - uses native browser APIs
 */
function downloadFile(
  content: string | Blob,
  filename: string,
  mimeType: string,
): void {
  const blob =
    content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export table to CSV (no external dependencies)
 */
export function exportTableToCSV(
  tableData: TableData,
  filename: string = 'table',
): void {
  const { headers, rows } = tableData;

  const csvContent = [
    headers.join(';'),
    ...rows.map((row) =>
      row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(';'),
    ),
  ].join('\n');

  downloadFile(
    '\ufeff' + csvContent,
    `${filename}.csv`,
    'text/csv;charset=utf-8;',
  );
}
