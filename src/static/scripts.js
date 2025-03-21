document.getElementById("upload-form").addEventListener("submit", function (e) {
  e.preventDefault();

  const formData = new FormData(this);

  fetch("/analyze", {
    method: "POST",
    body: formData
  })
    .then(res => res.json())
    .then(data => {
      const section = document.getElementById("results-section");
      const table = document.getElementById("results-table");
      table.innerHTML = "";

      if (data.length === 0) {
        table.innerHTML = "<tr><td colspan='4'>No matching CVs found.</td></tr>";
      } else {
        data.forEach((row) => {
          const tr = document.createElement("tr");
          tr.innerHTML = `
            <td>${row.uuid}</td>
            <td>${row.score}</td>
            <td>${row.reason}</td>
            <td><button onclick="viewCV('${row.uuid}')">📄 View</button></td>
          `;
          table.appendChild(tr);
        });
      }

      section.style.display = "block";
    })
    .catch(err => {
      alert("Error analyzing job description.");
      console.error(err);
    });
});

function viewCV(uuid) {
  const viewer = document.getElementById("cv-viewer");
  const iframe = document.getElementById("cv-iframe");
  iframe.src = `/attachment/${uuid}`;
  viewer.style.display = "block";
}

function closeViewer() {
  const viewer = document.getElementById("cv-viewer");
  const iframe = document.getElementById("cv-iframe");
  iframe.src = "";
  viewer.style.display = "none";
}
