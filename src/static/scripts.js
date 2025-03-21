let applicantsTable;

document.addEventListener('DOMContentLoaded', () => {
  initFileUpload();
  initFormSubmission();
});

const initFileUpload = () => {
  const fileInput = document.getElementById('job-file');
  const fileNameLabel = document.getElementById('file-name');
  const fileUploadContainer = document.getElementById('file-upload-container');

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      fileNameLabel.textContent = fileInput.files[0].name;
      fileNameLabel.style.display = 'inline';
      fileUploadContainer.classList.add('file-selected');
      showToast('File uploaded successfully!', 'success');
    } else {
      resetFileUpload();
    }
  });

  // Make the entire container clickable
  fileUploadContainer.addEventListener('click', (e) => {
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });
};

const resetFileUpload = () => {
  const fileNameLabel = document.getElementById('file-name');
  const fileUploadContainer = document.getElementById('file-upload-container');
  fileNameLabel.style.display = 'inline';
  fileNameLabel.textContent = 'Upload job description document';
  fileUploadContainer.classList.remove('file-selected');
};

const initFormSubmission = () => {
  const form = document.getElementById('upload-form');
  const loader = document.getElementById('loader');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const formData = new FormData(form);
    const jobText = formData.get('job_text');
    const jobFile = formData.get('job_file');

    if (!jobText && (!jobFile || jobFile.size === 0)) {
      showToast('Please enter job requirements or upload a document', 'error');
      return;
    }

    loader.classList.add('visible');

    fetch('/analyze', { method: 'POST', body: formData })
      .then(response => {
        if (!response.ok) throw new Error('Server error: ' + response.status);
        return response.json();
      })
      .then(data => {
        setTimeout(() => {
          loader.classList.remove('visible');
          displayResults(data);
          document.getElementById('results-section').style.display = 'block';
          
          // Add classes to adjust layout when results are shown
          document.getElementById('upload-section').classList.add('with-results');
          document.getElementById('results-section').classList.add('with-results');
          
          showToast(
            data.length 
              ? `Found ${data.length} qualified applicants!` 
              : 'No qualified applicants found', 
            data.length ? 'success' : 'warning'
          );
        }, 800);
      })
      .catch(error => {
        loader.classList.remove('visible');
        showToast('Error analyzing job requirements: ' + error.message, 'error');
        console.error(error);
      });
  });
};

const displayResults = (data) => {
  const resultsTable = document.getElementById('results-table');
  const resultCount = document.getElementById('result-count');
  resultsTable.innerHTML = '';
  
  if (data.length) {
    resultCount.textContent = `(${data.length})`;
  } else {
    resultCount.textContent = '';
  }

  // Destroy existing DataTable if it exists
  if (applicantsTable) {
    applicantsTable.destroy();
  }

  if (!data.length) {
    resultsTable.innerHTML = `
      <tr>
        <td colspan="4" class="no-results">
          <i class="fas fa-search"></i>
          <h3>No qualified applicants found</h3>
          <p>Try adjusting your job requirements or expanding search criteria.</p>
        </td>
      </tr>
    `;
    return;
  }

  data.sort((a, b) => b.score - a.score);
  data.forEach((result, index) => {
    const tr = document.createElement('tr');
    const scoreColor = result.score > 0.85 
      ? 'var(--success)' 
      : (result.score < 0.7 ? 'var(--warning)' : 'var(--orange)');
    const scorePercentage = Math.round(result.score * 100);
    
    tr.innerHTML = `
      <td>
        <div class="file-info">
          <i class="fas fa-user-tie"></i>
          <span>Applicant ${index + 1}</span>
        </div>
      </td>
      <td>
        <span class="score-pill" style="background: ${scoreColor};">${scorePercentage}%</span>
      </td>
      <td>${result.reason}</td>
      <td>
        <button class="btn btn-orange" onclick="viewCV('${result.uuid}')">
          <i class="fas fa-eye"></i> View
        </button>
      </td>
    `;
    resultsTable.appendChild(tr);
  });
  
  // Initialize DataTable with responsive options
  applicantsTable = $('#applicants-table').DataTable({
    responsive: true,
    pageLength: 5,
    lengthMenu: [5, 10, 25, 50],
    scrollX: false,
    autoWidth: false,
    language: {
      search: "Find applicant:",
      lengthMenu: "Show _MENU_ applicants",
      info: "Showing _START_ to _END_ of _TOTAL_ applicants",
      paginate: {
        first: '<i class="fas fa-angle-double-left"></i>',
        last: '<i class="fas fa-angle-double-right"></i>',
        next: '<i class="fas fa-angle-right"></i>',
        previous: '<i class="fas fa-angle-left"></i>'
      }
    },
    columnDefs: [
      { width: "15%", targets: 0 },
      { width: "15%", targets: 1, className: 'text-center' },
      { width: "55%", targets: 2 },
      { width: "15%", targets: 3, className: 'text-center' }
    ]
  });
};

const showToast = (message, type = 'info') => {
  const toastContainer = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  let icon = 'fa-info-circle';
  if (type === 'success') icon = 'fa-check-circle';
  if (type === 'warning') icon = 'fa-exclamation-triangle';
  if (type === 'error') icon = 'fa-times-circle';

  toast.innerHTML = `<i class="fas ${icon}"></i> <span>${message}</span>`;
  toastContainer.appendChild(toast);
  
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 4000);
};

const viewCV = (uuid) => {
  const viewer = document.getElementById('cv-viewer');
  const iframe = document.getElementById('cv-iframe');
  const modalTitle = document.getElementById('modal-title');
  
  modalTitle.textContent = 'Loading Resume...';
  iframe.src = `/attachment/${uuid}`;
  viewer.classList.add('show');
  
  // Update title once loaded
  iframe.onload = () => {
    modalTitle.textContent = 'Applicant Resume';
  };
  
  // Set up download button
  document.getElementById('download-pdf').onclick = () => {
    window.open(`/attachment/${uuid}?download=true`, '_blank');
  };
};

const closeViewer = () => {
  const viewer = document.getElementById('cv-viewer');
  viewer.classList.remove('show');
  setTimeout(() => {
    document.getElementById('cv-iframe').src = '';
  }, 300);
};