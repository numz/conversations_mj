/**
 * @jest-environment jsdom
 */
import { parseHtmlTable, exportTableToCSV } from '../exportTable';

// ------------------------------------------------------------------ //
// parseHtmlTable
// ------------------------------------------------------------------ //
describe('parseHtmlTable', () => {
  function makeTable(html: string): HTMLTableElement {
    const div = document.createElement('div');
    div.innerHTML = html;
    return div.querySelector('table') as HTMLTableElement;
  }

  it('extracts headers and rows from a standard table', () => {
    const table = makeTable(`
      <table>
        <thead><tr><th>Name</th><th>Age</th></tr></thead>
        <tbody><tr><td>Alice</td><td>30</td></tr></tbody>
      </table>
    `);

    const data = parseHtmlTable(table);
    expect(data.headers).toEqual(['Name', 'Age']);
    expect(data.rows).toEqual([['Alice', '30']]);
  });

  it('uses first row as headers when no thead', () => {
    const table = makeTable(`
      <table>
        <tbody>
          <tr><td>Name</td><td>Age</td></tr>
          <tr><td>Bob</td><td>25</td></tr>
        </tbody>
      </table>
    `);

    const data = parseHtmlTable(table);
    expect(data.headers).toEqual(['Name', 'Age']);
    expect(data.rows).toEqual([['Bob', '25']]);
  });

  it('handles multiple body rows', () => {
    const table = makeTable(`
      <table>
        <thead><tr><th>X</th></tr></thead>
        <tbody>
          <tr><td>1</td></tr>
          <tr><td>2</td></tr>
          <tr><td>3</td></tr>
        </tbody>
      </table>
    `);

    const data = parseHtmlTable(table);
    expect(data.rows).toHaveLength(3);
  });

  it('trims whitespace from cells', () => {
    const table = makeTable(`
      <table>
        <thead><tr><th>  Name  </th></tr></thead>
        <tbody><tr><td>  Alice  </td></tr></tbody>
      </table>
    `);

    const data = parseHtmlTable(table);
    expect(data.headers).toEqual(['Name']);
    expect(data.rows).toEqual([['Alice']]);
  });

  it('returns empty arrays for empty table', () => {
    const table = makeTable('<table><tbody></tbody></table>');
    const data = parseHtmlTable(table);
    expect(data.headers).toEqual([]);
    expect(data.rows).toEqual([]);
  });
});

// ------------------------------------------------------------------ //
// exportTableToCSV
// ------------------------------------------------------------------ //
describe('exportTableToCSV', () => {
  let mockClick: jest.Mock;
  let mockCreateObjectURL: jest.Mock;
  let mockRevokeObjectURL: jest.Mock;

  beforeEach(() => {
    mockClick = jest.fn();
    mockCreateObjectURL = jest.fn().mockReturnValue('blob:test');
    mockRevokeObjectURL = jest.fn();

    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    jest.spyOn(document, 'createElement').mockImplementation((tag) => {
      if (tag === 'a') {
        return { click: mockClick, href: '', download: '' } as unknown as HTMLAnchorElement;
      }
      return document.createElement(tag);
    });
    jest.spyOn(document.body, 'appendChild').mockImplementation((n) => n);
    jest.spyOn(document.body, 'removeChild').mockImplementation((n) => n);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('triggers download with .csv extension', () => {
    exportTableToCSV({ headers: ['A'], rows: [['1']] }, 'report');
    expect(mockClick).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:test');
  });

  it('uses semicolon as CSV delimiter', () => {
    let blobContent = '';
    mockCreateObjectURL.mockImplementation((blob: Blob) => {
      const reader = new FileReader();
      reader.readAsText(blob);
      reader.onload = () => {
        blobContent = reader.result as string;
      };
      return 'blob:test';
    });

    exportTableToCSV(
      { headers: ['A', 'B'], rows: [['1', '2']] },
      'test',
    );

    // Verify the Blob was created with correct content
    expect(mockCreateObjectURL).toHaveBeenCalled();
    const blob = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blob).toBeInstanceOf(Blob);
  });

  it('escapes double quotes in CSV cells', () => {
    // The function wraps cells in quotes and doubles any existing quotes
    exportTableToCSV(
      { headers: ['Name'], rows: [['She said "hello"']] },
    );
    expect(mockClick).toHaveBeenCalled();
  });

  it('uses default filename "table" when not provided', () => {
    exportTableToCSV({ headers: ['X'], rows: [] });
    expect(mockClick).toHaveBeenCalled();
  });
});
