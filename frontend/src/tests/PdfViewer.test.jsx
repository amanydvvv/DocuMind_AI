import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import * as api from '../services/api';
import PdfViewer from '../components/pdf/PdfViewer';

const mocks = vi.hoisted(() => ({
  simulateError: false,
  lastDocumentProps: null,
}));

afterEach(cleanup);

vi.mock('react-pdf', () => {
  const React = require('react');
  const Document = (props) => {
    mocks.lastDocumentProps = props;
    React.useEffect(() => {
      if (mocks.simulateError) {
        props.onLoadError?.(new Error('The source file is no longer available.'));
      } else {
        props.onLoadSuccess?.({ numPages: 50 });
      }
    }, []);
    return React.createElement('div', null, props.children || null);
  };
  const Page = (props) =>
    React.createElement(
      'div',
      { 'data-testid': 'pdf-page', 'data-page': props.pageNumber },
      `Page ${props.pageNumber}`
    );
  return {
    Document,
    Page,
    pdfjs: { GlobalWorkerOptions: {} },
  };
});

describe('PdfViewer', () => {
  it('mounts and passes the cited page number to the PDF Page renderer', async () => {
    render(<PdfViewer documentId="doc-1" filename="report.pdf" pageNumber={42} onClose={() => {}} />);

    const pageEl = await screen.findByTestId('pdf-page');
    expect(pageEl.getAttribute('data-page')).toBe('42');
    expect(screen.getByText('report.pdf')).toBeTruthy();
    expect(screen.getByTestId('page-indicator').textContent).toContain('Page 42 of 50');
  });

  it('requests the document from the scoped file endpoint with auth headers', async () => {
    localStorage.setItem('kuerycore_token', 'test-token');
    render(<PdfViewer documentId="doc-abc" filename="r.pdf" pageNumber={1} onClose={() => {}} />);
    await screen.findByTestId('pdf-page');

    expect(mocks.lastDocumentProps.file.url).toBe(
      `${api.API_URL}/api/documents/doc-abc/file`
    );
    expect(mocks.lastDocumentProps.file.httpHeaders).toHaveProperty(
      'Authorization',
      'Bearer test-token'
    );
    localStorage.removeItem('kuerycore_token');
  });

  it('defaults to page 1 when a document only cites page 1', async () => {
    render(<PdfViewer documentId="doc-1" filename="one.pdf" pageNumber={1} onClose={() => {}} />);
    const pageEl = await screen.findByTestId('pdf-page');
    expect(pageEl.getAttribute('data-page')).toBe('1');
  });

  it('lands on a late page (40+) and does not default to page 1', async () => {
    render(<PdfViewer documentId="doc-1" filename="long.pdf" pageNumber={47} onClose={() => {}} />);
    const pageEl = await screen.findByTestId('pdf-page');
    expect(pageEl.getAttribute('data-page')).toBe('47');
  });

  it('navigates pages with prev/next and clamps at document bounds', async () => {
    render(<PdfViewer documentId="doc-1" filename="nav.pdf" pageNumber={47} onClose={() => {}} />);
    await screen.findByTestId('pdf-page');

    fireEvent.click(screen.getByText('Next →'));
    expect(screen.getByTestId('pdf-page').getAttribute('data-page')).toBe('48');

    fireEvent.click(screen.getByText('← Prev'));
    expect(screen.getByTestId('pdf-page').getAttribute('data-page')).toBe('47');
  });

  it('shows a visible error state when the document is missing/unavailable', async () => {
    mocks.simulateError = true;
    render(<PdfViewer documentId="doc-gone" filename="gone.pdf" pageNumber={1} onClose={() => {}} />);

    expect(await screen.findByText('Document unavailable')).toBeTruthy();
    expect(screen.getByText('The source file is no longer available.')).toBeTruthy();
    expect(screen.queryByTestId('pdf-page')).toBeNull();
    mocks.simulateError = false;
  });
});

describe('CitationViewer view-in-document action', () => {
  it('invokes onViewDocument with the citation when clicked', async () => {
    const CitationViewer = (await import('../components/shared/CitationViewer')).default;
    const onViewDocument = vi.fn();
    const citation = {
      chunk_id: 'chunk-1',
      document_id: 'doc-1',
      filename: 'report.pdf',
      page_number: 12,
    };

    render(
      <CitationViewer citation={citation} onClose={() => {}} onViewDocument={onViewDocument} />
    );

    fireEvent.click(screen.getByText('View in document'));
    expect(onViewDocument).toHaveBeenCalledWith(citation);
  });
});