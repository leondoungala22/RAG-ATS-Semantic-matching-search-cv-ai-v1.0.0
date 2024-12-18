# prompt_template.py

def get_create_structured_cv_prompt_template_text():
    """
    Returns a detailed and clear prompt for structuring multi-page CVs into a MongoDB-compatible, hierarchical key-value format
    and valid JSON format, universally adaptable to all profile types.
    """
    return (
        """
        As the world wide expert ever for ATS CV, follow the following istructions: 
        ### Guidelines:
        - Respond in **plain text**, following the structured format below.
        - Ensure the output is in **valid JSON format** compatible with MongoDB, with all keys and values correctly formatted.
        - **Use a hierarchical JSON structure**, organizing the data in nested objects and arrays where appropriate.
        - **Standardize the format** to ensure consistency across different CVs.
        - **Extract all possible useful details** from the entire CV, leaving nothing relevant out. The goal is to capture **every detail that provides insight into the candidate's profile**.
        - The JSON must have **proper key-value pairs**, with keys enclosed in double quotes (`"key": "value"`).
        - Ensure no extra commas, trailing commas, or syntax errors.
        - **If a section is missing (for example, some profiles include additional sections while others do not), skip it and do not include it in the output. Therefore, never return empty keys.**
        - If the entire CV is empty, skip it and do not include it in the output.
        ### WARNING !!!! Never generate OR INVENT fake informations , this cvs should extaclly reflect the original ones . These cv will be use to retrive the most relevant candidcat based on job description . 

        **Handling Multi-Page CVs**:
        - Process the CV sequentially across pages, ensuring data from each page is merged without duplication.
        - Consolidate repetitive sections and ensure clarity without losing details.

        **Key Sections to Include** (adaptable to all profile types):

        - `informazioni_personali` (Personal Information): Include the following details when available (all fields are required if available, especially in this section and for all profile types):
          - **nome_completo** (Full name): The candidate's full legal name.
          - **contatti** (Contact information): A nested object containing:
            - **email**: Email addresses (**Always required** if available).
            - **telefoni**: Phone numbers.
            - **social_media**: Social media links (e.g., LinkedIn, Skype).
          - **indirizzo** (Address): A nested object containing:
            - **indirizzo**: Complete street address.
            - **città_residenza**: City of residence.
            - **cap**: Postal code (**Required**).
            - **paese_residenza**: Country of residence.
          - **nazionalità** (Nationality): The candidate's nationality or citizenship status.
          - **data_nascita** (Date of birth): Include if available.
          - **identificativi** (Identifiers): Any personal identifiers like ID numbers if present.
          - **titolo_professionale** (Job title):  based on the candidate's CV , The candidate's current or most recent job title (**Always required**).
          - **posizione_interesse** (Job of interest):  based on the candidate's CV , The position or role the candidate is seeking (**Always required**).
          - **seniority** (Seniority): Identify, based on the candidate's CV, the seniority for the position of interest (**Always required**).
          - **disponibilità** (Availability): Information about the candidate's availability, such as immediate availability, notice period, willingness to relocate, or travel preferences.
          - **link_github** (GitHub link): Include the candidate's GitHub profile URL if available; if not, skip this.

        - `sommario_esecutivo` (Executive Summary): A **comprehensive overview** from the complete CV, highlighting the individual’s core competencies, years of experience, key achievements, career goals, and unique strengths. **Do not summarize; aim to provide a full professional picture.**

        - `approfondimenti_profilo` (Profile Insights): Detailed insights into the individual's skills, career progression, areas of expertise, leadership qualities, and how they align with industry trends or future goals.

        - **Riepilogo Esecutivo**:
            - **Anni di Esperienza**: Total years of professional experience, if provided.
            - **Competenze Principali**: A list of the individual’s key skills, expertise, and areas of proficiency.
            - **Principali Risultati**: Highlight significant professional achievements, such as projects or milestones.
            - **Obiettivo Professionale**: The individual’s career objectives or goals, if provided.
        
        - **Profile Insights**:
            - **Global Experience and Mobility**: Provide details on the individual’s international experience, including any countries they’ve worked in or relocated to.
            - **Potential Career Trajectory**: Suggest potential future career paths based on the individual's skills, experience, and goals.
            - **Market Alignment**: Assess how well the individual’s skills align with current market demands and trends.
            - **Key Competencies**: Identify and summarize the core technical and soft skills based on the individual's qualifications, job roles, and any specific certifications or achievements mentioned in the CV. Highlight areas of expertise such as leadership, project management, technical proficiency, and industry-specific knowledge.
            - **Unique Skillset**: Identify skills or experiences that distinguish the candidate from others in the same field. This could include niche expertise, rare technical skills, interdisciplinary knowledge, or unique career accomplishments that are not commonly found in other candidates with similar job roles.
            - **Professional Development and Growth**: Analyze the progression of the individual’s career, including job titles, responsibilities, and achievements, to provide insight into their professional development. Assess if there is evidence of increasing responsibility, promotions, or skills acquired over time.

        - `competenze_tecniche` (Technical Skills): A list or nested object of relevant skills such as programming languages, tools, software, frameworks, methodologies, or any technical competencies specific to the individual's profession. Specify proficiency or expertise levels where applicable.

        - `esperienza_professionale` (Professional Experience): An array of objects, each containing:
          - **azienda** (Company): The name of the company.
          - **ruolo** (Role): Job title.
          - **periodo** (Period): Duration of employment.
          - **responsabilità** (Responsibilities): List of responsibilities and duties.
          - **risultati** (Achievements): Any significant contributions or accomplishments.

        - `formazione` (Education): An array or nested object containing:
          - **titoli** (Degrees): List of degrees earned.
          - **istituzioni** (Institutions): Institutions attended.
          - **date_laurea** (Graduation dates).
          - **argomenti_tesi** (Thesis topics), if applicable.
          - **certificazioni** (Certifications).
          - **onorificenze** (Honors).

        - `lingue` (Languages): An array of objects, each containing:
          - **lingua** (Language): The name of the language.
          - **livello** (Proficiency level): e.g., Madrelingua (Native), Fluente (Fluent), Conversazionale (Conversational).
          - **conoscenza_specializzata** (Specialized knowledge): Any specialized terminology knowledge.

        - `progetti` (Projects): For candidates with project experience, include:
          - **Only the top 4 most relevant projects**, selected based on their relevance to the CV's professional experience and career goals.
          - Each project should be an object containing:
            - **nome_progetto** (Project name).
            - **descrizione** (Description).
            - **tecnologie_utilizzate** (Technologies used), if applicable.
            - **ruolo** (Role in the project).
            - **impatto** (Impact of the project).
            - **link_repository** (Repository link): Provide the GitHub repository link for the project if available; if not, skip this.

        - `informazioni_aggiuntive` (Additional Information): Any other relevant details, such as hobbies, volunteer work, publications, presentations, conferences, awards, or other aspects that contribute to the individual’s profile.

        **Important Notes**:
        - **Use a hierarchical JSON structure**, organizing data into nested objects and arrays where appropriate, to reflect the relationships between different pieces of information.
        - **Standardize the format** to ensure consistency across different CVs.
        - Use **JSON-like key-value pairs** (e.g., `"key": "value"`) for clear and structured output.
        - All keys and values must be in **Italian**, including the keys themselves (e.g., `"nome_completo": "Giuseppe Verdi"`).
        - Do not include any additional comments.
        - **Skip any sections that are missing or incomplete; do not include them in the output.**
        - Focus on clarity, accuracy, and completeness in representing the CV’s content, organizing the information logically.
        - Use the provided CV content as the sole source of information; **do not summarize excessively or exclude details. Extract all useful information.**
          ### REMINDER WARNING !!!! Never generate fake informations , this cvs should extaclly reflect the original ones . These cv will be use to retrive the most relevant candidcat based on job description . 

        **Input Data**:
        - Testo originale del CV (CV Original Text): {extracted_text}
        - Progetti GitHub (GitHub Projects): {github_projects_text}

        Ensure that the output is **complete, well-organized**, uses a **hierarchical JSON structure**, and is in **valid JSON format**, even if the CV spans multiple pages.
        """
    )












def get_create_summary_prompt_template_text():
    """
    Returns the summary prompt template for CVs in a concise and professional style.
    """
    return (
        """
        Summarize the following CV, ensuring the response highlights only the most critical details. The summary should maximize conciseness while retaining important information.

        Use **Italian language** exclusively.

        # Output Format

        The CV content should be formatted in **plain text** to enable easy readability for a summarized overview.

        # Notes

        - Include only key details that summarize the qualifications effectively.
        - Maintain clarity to ensure a comprehensive yet concise representation.
        - Provide no additional comments—limit the response to the structured CV output only.
       NB : Use exclusively the **Italian language** for the response, regardless of the original language in the CV.


        CV Text: {extracted_text}

        # Useful CV Summary for HR
        """
    )
