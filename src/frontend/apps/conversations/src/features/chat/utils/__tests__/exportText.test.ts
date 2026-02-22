import { exportTextToTXT } from '../exportText';

describe('exportTextToTXT', () => {
  let appendChildSpy: jest.SpyInstance;
  let removeChildSpy: jest.SpyInstance;
  let mockCreateObjectURL: jest.Mock;
  let mockRevokeObjectURL: jest.Mock;
  let clickSpy: jest.Mock;

  beforeEach(() => {
    clickSpy = jest.fn();
    appendChildSpy = jest
      .spyOn(document.body, 'appendChild')
      .mockImplementation((node) => node);
    removeChildSpy = jest
      .spyOn(document.body, 'removeChild')
      .mockImplementation((node) => node);

    // jsdom doesn't have URL.createObjectURL/revokeObjectURL
    mockCreateObjectURL = jest.fn().mockReturnValue('blob:mock-url');
    mockRevokeObjectURL = jest.fn();
    global.URL.createObjectURL = mockCreateObjectURL;
    global.URL.revokeObjectURL = mockRevokeObjectURL;

    jest.spyOn(document, 'createElement').mockImplementation(
      (tag: string) =>
        ({
          tagName: tag.toUpperCase(),
          href: '',
          download: '',
          click: clickSpy,
          style: {},
        }) as unknown as HTMLElement,
    );
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('creates a blob with text/plain mime type', () => {
    exportTextToTXT('hello world', 'test');

    expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob));
    const blob = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blob.type).toBe('text/plain;charset=utf-8');
  });

  it('sets the download filename with .txt extension', () => {
    const link = { href: '', download: '', click: clickSpy, style: {} };
    jest
      .spyOn(document, 'createElement')
      .mockReturnValue(link as unknown as HTMLElement);

    exportTextToTXT('content', 'my_file');

    expect(link.download).toBe('my_file.txt');
  });

  it('uses default filename when none provided', () => {
    const link = { href: '', download: '', click: clickSpy, style: {} };
    jest
      .spyOn(document, 'createElement')
      .mockReturnValue(link as unknown as HTMLElement);

    exportTextToTXT('content');

    expect(link.download).toBe('document.txt');
  });

  it('clicks the link and cleans up', () => {
    exportTextToTXT('content', 'test');

    expect(clickSpy).toHaveBeenCalled();
    expect(appendChildSpy).toHaveBeenCalled();
    expect(removeChildSpy).toHaveBeenCalled();
    expect(mockRevokeObjectURL).toHaveBeenCalledWith('blob:mock-url');
  });

  it('handles empty content', () => {
    exportTextToTXT('', 'empty');

    expect(mockCreateObjectURL).toHaveBeenCalled();
    const blob = mockCreateObjectURL.mock.calls[0][0] as Blob;
    expect(blob.size).toBe(0);
  });
});
