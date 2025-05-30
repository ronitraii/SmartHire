# app.py
from flask import Flask, request, render_template, redirect, url_for, session
import pdfplumber
import docx
import os
import re
import json
import google.generativeai as genai 
import logging
import traceback
import datetime
from operator import itemgetter
import uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'resume_parser_secret_key'  # Needed for session
UPLOAD_FOLDER = 'uploads'
RESULTS_DB = 'candidates_results.json'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure your Google API Key
genai.configure(api_key="AIzaSyAvNuo_Hf6nHX3DCIOVi412_w42C7GTM-k")

def load_results_db():
    """Load the results database from file"""
    if os.path.exists(RESULTS_DB):
        try:
            with open(RESULTS_DB, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading results database: {str(e)}")
            return []
    return []

def save_to_results_db(result):
    """Save result to the database file"""
    try:
        # Add timestamp to the result
        result['timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Add unique ID for the result
        result['id'] = str(uuid.uuid4())
        
        # Load existing data
        results = load_results_db()
        
        # Add new result
        results.append(result)
        
        # Save back to file
        with open(RESULTS_DB, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Saved candidate {result.get('name')} to database")
        return result
    except Exception as e:
        logger.error(f"Error saving to results database: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def get_top_candidates(limit=3):
    """Get top candidates based on match percentage"""
    try:
        results = load_results_db()
        if not results:
            return []
            
        # Sort by match_percentage in descending order
        sorted_results = sorted(results, key=itemgetter('match_percentage'), reverse=True)
        
        # Return top candidates
        return sorted_results[:limit]
    except Exception as e:
        logger.error(f"Error getting top candidates: {str(e)}")
        logger.error(traceback.format_exc())
        return []

def extract_text(file_path):
    try:
        if file_path.endswith('.pdf'):
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted
            return text
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        else:
            logger.error(f"Unsupported file format: {file_path}")
            return ""
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        logger.error(traceback.format_exc())
        return ""

def analyze_with_gemini(tags_input, resume_text):
    try:
        if not resume_text or len(resume_text.strip()) == 0:
            logger.error("Empty resume text provided to analyze_with_gemini")
            return None
        
        # Process comma-separated tags
        tags_list = [tag.strip() for tag in tags_input.split(',') if tag.strip()]
        tags_formatted = ", ".join(tags_list)
        
        # Change model to the latest version
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        
        # Try a more simplified and explicit prompt
        prompt = f"""
You are a JSON-only resume analyzer. Respond ONLY with valid JSON, no explanations.

Analyze this resume text: {resume_text[:5000]}

Create a JSON object with exactly this structure, where each skill is checked for presence:
{{
  "name": "extracted name",
  "email": "extracted email",
  "phone": "extracted phone number or 'Not found'",
  "address": "extracted address or 'Not found'",
  "skills": [
    {{ "skill": "skill1", "present": true/false }},
    {{ "skill": "skill2", "present": true/false }}
  ]
}}

Skills to check: {tags_formatted}

Look thoroughly for phone numbers (any format like XXX-XXX-XXXX, (XXX) XXX-XXXX, etc.) and address information.
If phone or address isn't found, use the value "Not found" in the respective fields.
"""

        response = model.generate_content(prompt)
        
        if hasattr(response, 'text'):            
            # Parse JSON response with multiple fallback methods
            try:
                # Try to extract JSON if it's wrapped in backticks
                response_text = response.text.strip()
                
                # Method 1: Find JSON between backticks if they exist
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
                if json_match:
                    result_json = json.loads(json_match.group(1))
                    logger.info("Successfully parsed JSON from code block")
                else:
                    # Method 2: Try to find the JSON object directly
                    json_match = re.search(r'({[\s\S]*})', response_text)
                    if json_match:
                        result_json = json.loads(json_match.group(1))
                        logger.info("Successfully parsed JSON from regex match")
                    else:
                        # Method 3: Just try the whole text
                        result_json = json.loads(response_text)
                        logger.info("Successfully parsed JSON from full response")
                
                # Calculate match percentage
                total_skills = len(result_json.get('skills', []))
                matched_skills = sum(1 for skill in result_json.get('skills', []) if skill.get('present', False))
                
                # Add rejected skills list
                result_json['rejected_skills'] = [
                    skill['skill'] for skill in result_json.get('skills', []) 
                    if not skill.get('present', False)
                ]
                
                # Add matched skills list
                result_json['matched_skills'] = [
                    skill['skill'] for skill in result_json.get('skills', []) 
                    if skill.get('present', True)
                ]
                
                match_percentage = 0
                if total_skills > 0:
                    match_percentage = (matched_skills / total_skills) * 100
                
                # Add match percentage and approval status
                result_json['match_percentage'] = round(match_percentage)
                # Set Passing Percentage
                result_json['approved'] = match_percentage >= 80
                
                return result_json
            
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                logger.error(f"Response received: {response.text}")
                return None
        else:
            # Handle different response formats
            logger.error("Unexpected response format from Gemini API")
            logger.error(f"Response object: {response}")
            return None
    except Exception as e:
        logger.error(f"Error with Gemini API: {str(e)}")
        logger.error(traceback.format_exc())
        return None

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/parse", methods=["POST"])
def parse_resume():
    try:
        tags = request.form['tags']
        
        if 'resumes' not in request.files:
            return render_template("index.html", error="No file part in the request")
            
        uploaded_files = request.files.getlist('resumes')
        
        if not uploaded_files or uploaded_files[0].filename == '':
            return render_template("index.html", error="No file selected")

        results = []
        
        # Process each uploaded file
        for file in uploaded_files:
            # Ensure the file has an allowed extension
            if not (file.filename.lower().endswith('.pdf') or file.filename.lower().endswith('.docx')):
                continue  # Skip unsupported files
                
            # Skip this File Saving part
            # Generate unique filename
            filename = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            logger.info(f"File saved to {file_path}")

            resume_text = extract_text(file_path)
            
            if not resume_text or len(resume_text.strip()) == 0:
                # Skip files with no extractable text
                logger.warning(f"No text could be extracted from {file.filename}")
                continue

            result = analyze_with_gemini(tags, resume_text)
            
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except Exception as e:
                logger.error(f"Error removing file: {str(e)}")
            
            if result is None:
                continue  # Skip files that couldn't be analyzed
                
            # Save result to database and add to results list
            saved_result = save_to_results_db(result)
            if saved_result:
                results.append(saved_result)
        
        if not results:
            return render_template("index.html", error="Failed to analyze any of the uploaded resumes. Please try again.")
        
        # Redirect to appropriate page based on number of files
        if len(results) == 1:
            # Store single result in session for results page
            session['analysis_result'] = results[0]
            session['tags'] = tags
            return redirect(url_for('results'))
        else:
            # Store multiple results for top_candidates page
            session['batch_results'] = results
            return redirect(url_for('batch_results'))

    except Exception as e:
        logger.error(f"Error in parse_resume: {str(e)}")
        logger.error(traceback.format_exc())
        return render_template("index.html", error=f"An error occurred: {str(e)}")

@app.route("/results")
def results():
    analysis_result = session.get('analysis_result')
    tags = session.get('tags')
    
    if not analysis_result:
        return redirect(url_for('index'))
    
    return render_template("results.html", result=analysis_result, tags=tags)

@app.route("/batch-results")
def batch_results():
    batch_results = session.get('batch_results', [])
    
    if not batch_results:
        return redirect(url_for('top_candidates'))
    
    # Sort by match percentage in descending order
    sorted_results = sorted(batch_results, key=itemgetter('match_percentage'), reverse=True)
    
    return render_template("top_candidates.html", candidates=sorted_results, batch_mode=True)

@app.route("/top-candidates")
def top_candidates():
    top = get_top_candidates(3)
    return render_template("top_candidates.html", candidates=top)

if __name__ == "__main__":
    app.run(debug=True)