from flask import Flask, render_template, request
import re
import os
import matplotlib.pyplot as plt
import PyPDF2
import docx
from fuzzywuzzy import process

app = Flask(__name__)

# Master Skill List for Extraction
master_skill_list = [
    # Programming Languages
    "python", "java", "c++", "c", "c#", "javascript", "typescript", 
    "ruby", "php", "swift", "kotlin", "go", "rust", "scala", "r", 
    "dart", "perl", "bash", "sql", 
    # Add other categories as needed...
]

# Synonym Dictionary
synonym_dict = {
    "machine learning": ["ml", "deep learning", "artificial intelligence"],
    "data scientist": ["data science", "research scientist"],
    "nlp": ["natural language processing"],
    "python": ["py"],
}

# Function to Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.lower()

# Function to Extract Text from DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.lower()

# === Name Extraction Functions ===

def extract_name(text, filename=""):
    """
    1. Try full filename match inside text.
    2. Try first name + next word from text.
    3. Try pattern-based extraction.
    4 Try to infer name from email address.
    5. Fallback: filename cleaned first part or "Name Not Found".
    """
    clean_filename = clean_and_extract_name_from_filename(filename)

    # 1. Full clean filename match
    if clean_filename and name_appears_in_text(clean_filename, text):
        return clean_filename

    # 2. First name matching
    name_using_firstname = extract_name_from_text_using_filename(text, filename)
    if name_using_firstname != "Name Not Found":
        return name_using_firstname

    # 3. Pattern-based fallback
    name_from_text = extract_name_from_text(text)
    if name_from_text != "Name Not Found":
        return name_from_text

    #4 Try extracting name from email
    name_from_email = extract_name_from_email(text)
    if name_from_email != "Name Not Found":
        return name_from_email

    # 5. Last fallback
    return clean_filename if clean_filename else "Name Not Found"
def extract_name_from_email(text):
    print(text)
    """
    Extract possible name from email and attempt to find it in the text.
    If a progressive substring of the username appears in the text, use that to extract the full name.
    """
    email_match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    if not email_match:
        return "Name Not Found"

    email = email_match.group()


    username = email.split('@')[0]


    # Try progressively larger parts of the username (3, 4, 5 characters, etc.)
    name_parts = []
    for length in range(3, len(username)+1):
        part = username[:length]


        # Check if this part exists in the extracted text
        words = text.lower().split()
        if part.lower() in words:


            # If found, try to take the next word as the last name
            for i, word in enumerate(words):
                if word == part.lower() and i + 1 < len(words):
                    next_word = words[i + 1]
                    if next_word.isalpha() and len(next_word) > 1:
                        full_name = f"{word} {next_word}"
   
                        return full_name.title()

   
    return "Name Not Found"

def clean_and_extract_name_from_filename(filename):
    if not filename:
        return None
    base = os.path.splitext(filename)[0]  # Remove .pdf or .docx
    base = re.sub(r'\b(cv|resume|vitae|profile|application)\b', '', base, flags=re.IGNORECASE)

    base = base.replace('-', ' ')          # replace dashes with space
    base = base.replace('_', ' ')           # replace underscores with space
    base = re.sub(r"'s\b", '', base)         # remove possessive 's
    base = re.sub(r'[^a-zA-Z\s]', '', base)  # remove everything except letters and spaces
    clean = base.strip()

    clean = split_concatenated_names(clean)

    parts = [p for p in re.split(r'[\s]+', clean) if p]
    if len(parts) >= 2:
        if all(word[0].isupper() or word.isupper() for word in parts[:2]):
            return ' '.join(parts[:2]).title()
        else:
            return ' '.join(parts[:2]).title()
    elif len(parts) == 1:
        return parts[0].title()
    return None

def split_concatenated_names(text):
    # Look for patterns where two capitalized words are stuck together
    pattern = r'([a-z])([A-Z])'  # Matches a lowercase letter followed by an uppercase letter
    text = re.sub(pattern, r'\1 \2', text)  # Insert a space between lowercase and uppercase

    return text

def extract_name_from_text_using_filename(text, filename):
    """
    Attempt to extract the name by matching the filename first name with text.
    """
    clean_filename = clean_and_extract_name_from_filename(filename)
    if not clean_filename:
        return "Name Not Found"
    
    first_name = clean_filename.split()[0].lower()
    words = text.lower().split()

    for i, word in enumerate(words):
        if word == first_name and i + 1 < len(words):
            next_word = words[i + 1]
            if next_word.isalpha() and len(next_word) > 1:
                full_name = f"{word} {next_word}"
                return full_name.title()
    return "Name Not Found"

def extract_name_from_text(text):
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if lines and lines[0].isupper() and 2 <= len(lines[0].split()) <= 3:
        candidate = lines[0].title()
        if not has_contact_info(candidate):
            return candidate
    name_labels = ["name:", "full name:", "applicant:"]
    for line in lines[:10]:
        line_lower = line.lower()
        for label in name_labels:
            if label in line_lower:
                name = line[line_lower.index(label)+len(label):].strip()
                if name and not has_contact_info(name):
                    return name.title()
    for line in lines[:10]:
        if is_strong_name_candidate(line):
            return line.title()
    return "Name Not Found"

def name_appears_in_text(name, text):
    if not name or not text:
        return False
    variations = [
        name,
        name.upper(),
        name.replace(' ', '  '),
        name.replace(' ', '-')
    ]
    return any(v in text for v in variations)

def is_strong_name_candidate(text):
    words = text.split()
    return (2 <= len(words) <= 3 and
            all(word[0].isupper() for word in words) and
            not has_contact_info(text) and
            not any(len(word) == 1 for word in words))

def has_contact_info(text):
    contact_terms = ['@', 'http', 'github', 'linkedin', 'phone', 'tel', 'mobile']
    return (re.search(r'\d', text) or
            any(term in text.lower() for term in contact_terms))

# =====================================================


# Function to Extract Email from Text
def extract_email(text):
    # Clean up the text
    cleaned_text = clean_text(text)
    # Adjust regex to be more lenient with boundaries and handle spaces
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', re.IGNORECASE)
    # Search for email in cleaned text
    match = email_pattern.search(cleaned_text)
    if match:
        return match.group()  # If an email is found
    else:
        return "Email not found"  # If no email is found
def clean_text(text):
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Attempt to reconstruct broken email addresses
    text = re.sub(r'(@[a-zA-Z0-9._%+-]+)\s+([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'\1.\2', text)
    return text
# Function to Extract Phone Number from Text
def extract_phone_number(text):
    phone_pattern = re.compile(r'(\+?\d{1,4}[\s-])?(?:\(?\d{3}\)?[\s-]?)?\d{3}[\s-]?\d{4}')
    match = phone_pattern.search(text)
    return match.group() if match else "Phone number not found"

# Function to Extract Skills from Text (for demo purposes)
def extract_skills(text):
    skills = ["Python", "Java", "SQL", "Machine Learning"]
    found = [skill for skill in skills if skill.lower() in text.lower()]
    return found

# Function to Normalize Resume Skills (Handling Synonyms)
def normalize_skills(resume_skills):
    normalized_resume_skills = set()
    for skill in resume_skills:
        matched = False
        for key, synonyms in synonym_dict.items():
            if skill in synonyms or skill == key:
                normalized_resume_skills.add(key)
                matched = True
                break
        if not matched:
            normalized_resume_skills.add(skill)
    return normalized_resume_skills

# Function to Generate Visualization (Bar and Pie charts)
def generate_visualization(matched_skills, missing_skills, match_percentage):
    plt.switch_backend('Agg')
    matched_skills = sorted(list(matched_skills))  # sort matched skills alphabetically
    missing_skills = sorted(list(missing_skills))  # sort missing skills alphabetically

    skills = matched_skills + missing_skills
    presence = [1] * len(skills)
    colors = ["green"] * len(matched_skills) + ["#A00000CC"] * len(missing_skills)

    # Bar Chart
    plt.figure(figsize=(10, 6))
    plt.bar(skills, presence, color=colors)
    plt.xlabel("Skills")
    plt.ylabel("Presence")
    plt.title("Comparison of Skills: Matched vs Unmatched Based on Job Requirements")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("static/bar_chart.png")
    plt.close()

    # Pie Chart
    plt.figure(figsize=(10, 6))
    plt.pie([match_percentage, 100 - match_percentage], labels=["Matched", "Not Matched"], colors=["green", "#A00000CC"], autopct="%1.1f%%", startangle=140)
    plt.title("Resume Match Percentage")
    plt.savefig("static/pie_chart.png")
    plt.close()

# Function to Process Resume (Main Logic)
# Function to Process Resume (Main Logic)
def process_resume(resume_path, job_keywords):
    if resume_path.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    elif resume_path.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_path)
    else:
        return None, None, None, None, None

    filename = os.path.basename(resume_path)
    name = extract_name(resume_text, filename)  # Use extract_name instead of extract_name_from_filename
    email = extract_email(resume_text)
    phone = extract_phone_number(resume_text)
    skills = extract_skills(resume_text)

    normalized_resume_skills = normalize_skills(skills)
    final_matched_skills = set()

    for skill in normalized_resume_skills:
        best_match = process.extractOne(skill, job_keywords)
        if best_match and best_match[1] >= 90:
            final_matched_skills.add(best_match[0])

    match_percentage = round((len(final_matched_skills) / len(job_keywords)) * 100, 2)
    missing_skills = set(job_keywords) - final_matched_skills

    generate_visualization(final_matched_skills, missing_skills, match_percentage)

    return name, email, phone, final_matched_skills, match_percentage, missing_skills

# Flask Routes
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_keywords = request.form["job_description"].lower().split(",")
        job_keywords = [keyword.strip() for keyword in job_keywords]
        file = request.files["resume"]
        if file:
            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)
            name, email, phone, matched_skills, match_percentage, missing_skills = process_resume(filepath, job_keywords)
            os.remove(filepath)
            return render_template("result.html", name=name, email=email, phone=phone, skills=matched_skills, percentage=match_percentage)
    return render_template("index.html")

@app.route("/top-candidates")
def top_candidates():
    return "<h1>Top Candidates Page (Coming Soon!)</h1><a href='/'>Go Home</a>"

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
