document.addEventListener("DOMContentLoaded", function () {
    // Remove Professional Experience Log section
    const experienceLogSection = document.getElementById("experience-log-container");
    if (experienceLogSection) {
        experienceLogSection.remove();
        console.log("Professional Experience Log section removed.");
    }

    // Handle form submission to ensure job description is entered
    document.getElementById("searchForm").addEventListener("submit", function (event) {
        const jobDescription = document.getElementById("job_description").value.trim();
        if (!jobDescription) {
            event.preventDefault();
            document.getElementById("errorMessage").innerText = "Please provide a job description.";
        }
    });

    // Show results if available
    if (document.getElementById("results-container").dataset.hasResults === "true") {
        showResults();
    }
});

function showResults() {
    document.getElementById("search-container").style.display = "none";
    document.getElementById("results-container").style.display = "flex";
}


function showDetailedCV(documentId) {
    const resultsContainer = document.getElementById("results-container");
    const results = JSON.parse(resultsContainer.dataset.results || "[]");

    const candidate = results.find(result => result.document_id === documentId);

    if (candidate) {
        const detailsContainer = document.getElementById("cvDetailsContent");
        detailsContainer.innerHTML = ""; // Clear previous content

        const sectionOrder = [
            "Informazioni_personali",   // Personal Information
            "Sommario_esecutivo",       // Executive Summary
            "Approfondimenti_profilo",  // Profile Insights
            "Esperienza_professionale", // Professional Experience
            "Competenze_tecniche",      // Technical Skills
            "Formazione",               // Education
            "Lingue",                   // Languages
            "Informazioni_aggiuntive"   // Additional Information
        ];

        let detailsHTML = "";

        sectionOrder.forEach(sectionKey => {
            console.log(`Checking section: ${sectionKey}`);

            if (candidate.formatted_cv[sectionKey]) {
                const sectionData = candidate.formatted_cv[sectionKey];
                console.log(`Section ${sectionKey} found:`, sectionData);

                detailsHTML += `<div class="cv-section">
                    <h3>${sectionKey.replace(/_/g, " ")}</h3>`;

                if (sectionKey === "Esperienza_professionale") {
                    detailsHTML += renderProfessionalExperience(sectionData);
                } else if (sectionKey === "Formazione") {
                    detailsHTML += renderEducationSection(sectionData);
                } else {
                    detailsHTML += renderGenericSection(sectionData);
                }

                detailsHTML += `</div>`;
            } else {
                console.warn(`Section ${sectionKey} is missing in the CV data for ${documentId}`);
                detailsHTML += `<div class="cv-section">
                    <h3>${sectionKey.replace(/_/g, " ")}</h3>
                    <p class="missing-section">This section is not available.</p>
                </div>`;
            }
        });

        detailsContainer.innerHTML = detailsHTML;
    } else {
        console.error(`Candidate with ID ${documentId} not found.`);
    }
}

function renderProfessionalExperience(sectionData) {
    console.log("Rendering Professional Experience section...");

    let experienceHTML = "";

    // Ensure sectionData is an array or an object
    if (Array.isArray(sectionData)) {
        sectionData.forEach((experience, index) => {
            experienceHTML += `
                <div class="experience-entry">
                    <h4>Esperienza ${index + 1}</h4>
                    <p><strong>Azienda:</strong> ${experience.Azienda || "N/A"}</p>
                    <p><strong>Periodo:</strong> ${experience.Periodo || "N/A"}</p>
                    <p><strong>Ruolo:</strong> ${experience.Ruolo || "N/A"}</p>
                    <p><strong>Responsabilità:</strong></p>
                    <ul>
                        ${
                            Array.isArray(experience.Responsabilità)
                                ? experience.Responsabilità.map(item => `<li>${item}</li>`).join("")
                                : "<li>N/A</li>"
                        }
                    </ul>
                    ${
                        experience.Risultati
                            ? `<p><strong>Risultati:</strong></p>
                            <ul>${experience.Risultati.map(result => `<li>${result}</li>`).join("")}</ul>`
                            : ""
                    }
                </div>
                <hr class="section-separator">`;
        });
    } else if (typeof sectionData === "object" && sectionData !== null) {
        // Handle a single experience object
        experienceHTML += `
            <div class="experience-entry">
                <p><strong>Azienda:</strong> ${sectionData.Azienda || "N/A"}</p>
                <p><strong>Periodo:</strong> ${sectionData.Periodo || "N/A"}</p>
                <p><strong>Ruolo:</strong> ${sectionData.Ruolo || "N/A"}</p>
                <p><strong>Responsabilità:</strong></p>
                <ul>
                    ${
                        Array.isArray(sectionData.Responsabilità)
                            ? sectionData.Responsabilità.map(item => `<li>${item}</li>`).join("")
                            : "<li>N/A</li>"
                    }
                </ul>
                ${
                    sectionData.Risultati
                        ? `<p><strong>Risultati:</strong></p>
                        <ul>${sectionData.Risultati.map(result => `<li>${result}</li>`).join("")}</ul>`
                        : ""
                }
            </div>`;
    } else {
        console.warn("No professional experience data available.");
        experienceHTML += `<p class="missing-section">No professional experience available for this candidate.</p>`;
    }

    return experienceHTML;
}


function renderEducationSection(sectionData) {
    let educationHTML = "";

    if (sectionData) {
        const { Titoli, Istituzioni, Date_laurea, Certificazioni, Onorificenze } = sectionData;

        if (Titoli && Istituzioni && Date_laurea) {
            for (let i = 0; i < Titoli.length; i++) {
                educationHTML += `<div class="degree">
                    <h4>${Titoli[i]}</h4>
                    <p><strong>Institution:</strong> ${Istituzioni[i] || "N/A"}</p>
                    <p><strong>Date:</strong> ${Date_laurea[i] || "N/A"}</p>
                </div>`;
                if (i < Titoli.length - 1) {
                    educationHTML += `<hr class="section-separator">`;
                }
            }
        }

        if (Certificazioni && Certificazioni.length > 0) {
            educationHTML += `<h5>Certifications:</h5><ul>`;
            educationHTML += Certificazioni.map(cert => `<li>${cert}</li>`).join("");
            educationHTML += `</ul><hr class="section-separator">`;
        }

        if (Onorificenze && Onorificenze.length > 0) {
            educationHTML += `<h4>Honors:</h4><ul>`;
            educationHTML += Onorificenze.map(honor => `<li>${honor}</li>`).join("");
            educationHTML += `</ul>`;
        }
    }

    return educationHTML;
}

function renderGenericSection(sectionData) {
    let genericHTML = "";

    if (typeof sectionData === "object" && !Array.isArray(sectionData)) {
        genericHTML += Object.entries(sectionData)
            .map(([key, value]) => {
                if (Array.isArray(value)) {
                    return `<p><strong>${key.replace(/_/g, " ")}</strong>: 
                        <ul>${value.map(item => `<li>${item}</li>`).join("")}</ul></p>`;
                } else if (typeof value === "object") {
                    return `<p><strong>${key.replace(/_/g, " ")}</strong>: 
                        ${Object.entries(value)
                            .map(([subKey, subValue]) => `<span>${subKey}: ${subValue}</span>`)
                            .join(", ")}</p>`;
                } else {
                    return `<p><strong>${key.replace(/_/g, " ")}</strong>: ${value || "N/A"}</p>`;
                }
            })
            .join("");
    } else if (Array.isArray(sectionData)) {
        genericHTML += `<ul>${sectionData.map(item => `<li>${item}</li>`).join("")}</ul>`;
    } else {
        genericHTML += `<p>${sectionData || "N/A"}</p>`;
    }

    return genericHTML;
}

// Function to show and hide the search form
function showSearchForm() {
    const form = document.getElementById("searchForm");
    form.style.display = form.style.display === "none" ? "block" : "none";
}

function viewOriginalCV(documentId) {
    window.open(`/view_cv/${documentId}`, "Attached CV", "width=800,height=600");
}
