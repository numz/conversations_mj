/**
 * Text/Code block export utilities - no external dependencies
 */

/**
 * Download helper - uses native browser APIs
 */
function downloadFile(
  content: string,
  filename: string,
  mimeType: string,
): void {
  const blob = new Blob([content], { type: mimeType });
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
 * Export text content to TXT file
 */
export function exportTextToTXT(
  content: string,
  filename: string = 'document',
): void {
  downloadFile(content, `${filename}.txt`, 'text/plain;charset=utf-8');
}
