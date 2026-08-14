// src/tests/UploadPanel.test.jsx
import { render, fireEvent, screen, waitFor } from '@testing-library/react';
import UploadPanel from '../components/documents/UploadPanel';

// Mock the API service used by UploadPanel
jest.mock('../services/api', () => ({
  uploadDocument: jest.fn(),
  getDocument: jest.fn(),
}));

import { uploadDocument, getDocument } from '../services/api';

describe('UploadPanel - multi‑file support', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('selecting multiple files enqueues them and displays queue items', async () => {
    // Mock uploadDocument to resolve with a fake document id for each file
    uploadDocument.mockImplementation(() => Promise.resolve({ id: 'doc-123' }));
    // Mock getDocument to immediately report completed status
    getDocument.mockImplementation(() => Promise.resolve({ status: 'completed' }));

    const onUploadComplete = jest.fn();
    render(<UploadPanel onUploadComplete={onUploadComplete} />);

    const fileInput = screen.getByText(/drag & drop files here/i).parentElement?.querySelector('input[type="file"]');
    expect(fileInput).toBeInTheDocument();

    // Create two mock File objects
    const fileA = new File(['contentA'], 'fileA.pdf', { type: 'application/pdf' });
    const fileB = new File(['contentB'], 'fileB.txt', { type: 'text/plain' });

    // Simulate user selecting multiple files
    fireEvent.change(fileInput, { target: { files: [fileA, fileB] } });

    // The queue should now contain both file names
    await waitFor(() => {
      expect(screen.getByText('fileA.pdf')).toBeInTheDocument();
      expect(screen.getByText('fileB.txt')).toBeInTheDocument();
    });

    // Await asynchronous processing (upload + polling)
    await waitFor(() => {
      // Both items should have reached the "Done" badge
      expect(screen.getAllByText('Done').length).toBe(2);
    });

    // Verify onUploadComplete was called once after all files are done
    expect(onUploadComplete).toHaveBeenCalledTimes(1);
  });
});
