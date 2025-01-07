# **RAG-ATS Semantic Matching Search CV AI v1.0.0**  
> **An AI-powered Applicant Tracking System (ATS)** leveraging **Retrieval-Augmented Generation (RAG)** and semantic search to streamline CV analysis and improve talent acquisition workflows.

---

## 🌟 **Key Features**

- **🔍 Semantic Matching:** AI-powered search to match job descriptions with CVs intelligently.
- **📄 CV Parsing:** Automatically extracts and structures data from CVs for analysis.
- **📊 Candidate Ranking:** Ranks CVs by relevance to job descriptions using advanced embeddings.
- **💾 Database Integration:** Stores CVs and structured data in **Azure Cosmos DB** and attachments in **MySQL**.
- **🌐 Web Interface:** A user-friendly web application to upload, search, and view CVs dynamically.

---

## 📂 **Project Structure**

```plaintext
RAG-ATS-Semantic-Matching-Search-CV-AI/
├── src/
│   ├── augmenter/
│   │   ├── cv_processor.py         # Handles CV extraction, structuring, and saving
│   │   └── DataTools.py            # Converts files (e.g., .docx to .pdf)
│   ├── embedding/
│   │   └── embeddings.py           # Manages embeddings for vector search
│   ├── prompts/
│   │   └── prompt_templates.py     # Templates for structured CV generation
│   ├── retriever/
│   │   ├── helper_retriever.py     # Assists in similarity search and data retrieval
│   │   └── retriever.py            # Performs vector-based semantic search
│   ├── static/                     # Static assets (e.g., CSS, JS)
│   ├── templates/                  # HTML templates for the web app
│   ├── utils/
│   │   └── logger.py               # Logging utility
│   └── main.py                     # Entry point for the Flask web app
├── env/                            # Contains environment configuration
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation
```

---

## 🚀 **Getting Started**

### **Prerequisites**
- **Python**: Version 3.8 or higher.
- **Databases**:
  - **Azure Cosmos DB** for storing structured CVs.
  - **MySQL** for managing CV attachments.
- **APIs**:
  - **Anthropic Claude API** for generating structured CVs.
  - **Azure OpenAI API** for embeddings and semantic similarity.

### **Installation**
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/LeonDoungala22/RAG-ATS-Semantic-Matching-Search-CV-AI-v1.0.0.git
   cd RAG-ATS-Semantic-Matching-Search-CV-AI-v1.0.0
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the root directory and add:
   ```dotenv
   COSMOS_ENDPOINT=<your_cosmos_db_endpoint>
   COSMOS_KEY=<your_cosmos_db_key>
   MYSQL_USER_LOCAL=<your_mysql_user>
   MYSQL_PASSWORD_LOCAL=<your_mysql_password>
   MYSQL_HOST_LOCAL=<your_mysql_host>
   OPENAI_API_KEY=<your_openai_key>
   ANTHROPIC_API_KEY=<your_anthropic_key>
   ```

---

## 🎯 **Usage**

### **Running the Application**
1. **Start the Flask App**:
   ```bash
   python src/main.py
   ```
2. **Access the Web Interface**:
   Open your browser and navigate to `http://localhost:5000`.

### **Features**
- **Upload CVs**: Drag and drop your CVs in `.pdf` format.
- **Provide Job Descriptions**: Input detailed job descriptions.
- **View Results**: Get ranked CVs with structured data.

---

## 📊 **How It Works**

1. **Data Ingestion**:
   - Upload CVs in `.pdf` or `.docx` format.
   - Job descriptions are analyzed alongside CVs.
   
2. **CV Structuring**:
   - Text is extracted from CVs using **Anthropic Claude API**.
   - Key data (e.g., skills, experience, GitHub projects) is structured.

3. **Semantic Search**:
   - Uses **Azure OpenAI embeddings** for similarity scoring.
   - Performs a **vector-based search** in **Azure Cosmos DB**.
   - Results are re-ranked using dynamic thresholds and **Anthropic AI**.

4. **Presentation**:
   - Results are displayed with similarity scores and dynamic CV formatting.
   - Original CV attachments are accessible via **MySQL**.

---

## 🛠 **Technical Overview**

- **Framework**: Flask (Python)
- **Database**: Azure Cosmos DB (NoSQL), MySQL (relational)
- **AI Models**:
  - **Azure OpenAI Embeddings**: `text-embedding-ada-002`
  - **Anthropic Claude**: For CV structuring and re-ranking.
- **Deployment**:
  - Scalable architecture with support for cloud-based APIs and databases.

---

## 👨‍💻 **Contributing**

Contributions are welcome! Follow these steps:
1. Fork the repository.
2. Create a feature branch:
   ```bash
   git checkout -b feature/new-feature
   ```
3. Commit your changes and push:
   ```bash
   git push origin feature/new-feature
   ```
4. Create a pull request.

---

## 📄 **License**

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 📧 **Contact**

For questions or support, feel free to reach out:
- **GitHub**: [LeonDoungala22](https://github.com/LeonDoungala22)
- **Portfolio Website**: [leondoungala22.github.io](https://leondoungala22.github.io/doungala.leon.github.io/)
- **Email**: [doungala.leon@gmail.com](mailto:doungala.leon@gmail.com)

