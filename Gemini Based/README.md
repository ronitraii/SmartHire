Resume Skills Analyzer
Overview
This project is a web-based resume parser built with Flask and powered by Google's Gemini API. It allows users to upload resumes (PDF or DOCX), specify required skills, and analyze the resume for skill matches. The application extracts candidate details (name, email, phone, address), evaluates skills, calculates a match percentage, and stores results in a JSON database. Users can view individual analysis results and the top 3 candidates based on match percentage.
Prerequisites

Python 3.8 or higher
A Google API key for the Gemini API (set in app.py)
A modern web browser (Chrome, Firefox, etc.)

Setup Instructions
1. Clone the Repository
Clone or download the project to your local machine:
git clone <repository-url>
cd resume-skills-analyzer

2. Create and Activate a Virtual Environment
Create a virtual environment to isolate project dependencies:
python -m venv venv

Activate the virtual environment:

Windows:     venv\Scripts\activate


3. Install Dependencies
Install the required Python libraries listed in requirements.txt:
pip install -r requirements.txt

Example requirements.txt
Flask==2.3.2
pdfplumber==0.10.2
python-docx==0.8.11
google-generativeai==0.7.0

If you don't have a requirements.txt, create one with the above content or install the packages manually:
pip install Flask pdfplumber python-docx google-generativeai

4. Configure the Google API Key
Replace the placeholder API key in app.py with your Google API key for the Gemini API:
genai.configure(api_key="YOUR_API_KEY_HERE")

You can obtain a Google API key from the Google Cloud Console.
5. Run the Application
Start the Flask application by running:
python app.py

The application will start in debug mode and be accessible at http://127.0.0.1:5000 in your web browser.
Project Structure

app.py: Main Flask application with routes for uploading resumes, parsing, and displaying results.
templates/: HTML templates (index.html, results.html, top_candidates.html) for the web interface.
uploads/: Directory for temporarily storing uploaded resume files (created automatically).
candidates_results.json: JSON file storing candidate analysis results (created automatically).
static/: (Optional) Directory for static assets like CSS or JavaScript (not used in this project).
requirements.txt: List of Python dependencies.

Usage

Open http://127.0.0.1:5000 in your browser.
Enter comma-separated skills (e.g., Python, Java, SQL) and upload a resume (PDF or DOCX).
Click "Analyze Resume" to view the analysis, including candidate details, skill matches, and match percentage.
Click "Show Top 3 Candidates" to view the top candidates based on match percentage.
Results are saved to candidates_results.json for persistence.

Notes

Ensure the uploads directory and candidates_results.json are writable by the application.
The Gemini API key must be valid and have appropriate permissions.
Debug mode is enabled by default (app.run(debug=True)). Disable it in production for security.

Troubleshooting

ModuleNotFoundError: Ensure all dependencies are installed and the virtual environment is activated.
API Errors: Verify your Google API key and Gemini API access.
File Upload Issues: Check that uploaded files are valid PDF or DOCX files.

License
This project is licensed under the MIT License.
