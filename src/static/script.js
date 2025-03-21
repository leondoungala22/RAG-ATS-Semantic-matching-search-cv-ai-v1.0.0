document.getElementById("job-form").addEventListener("submit", async function (e) {
  e.preventDefault();

  const formData = new FormData(this);

  const response = await fetch("/analyze", {
      method: "POST",
      body: formData,
  });

  const resultContainer = document.getElementById("cv-list");
  resultContainer.innerHTML = "";

  if (!response.ok) {
      const error = await response.json();
      alert(error.error || "Something went wrong.");
      return;
  }

  const results = await response.json();
  results.forEach(item => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>ID:</strong> ${item.id}<br><strong>Score:</strong> ${item.score}<br><strong>Reason:</strong> ${item.reason}`;
      resultContainer.appendChild(li);
  });
});
