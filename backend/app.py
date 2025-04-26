from flask import Flask, render_template, request
import os
import re
import string
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PyPDF2 import PdfReader
import docx
from fuzzywuzzy import process
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
from fuzzywuzzy import fuzz

app = Flask(__name__)

# Synonym Dictionary for Skill Matching
# Synonym Dictionary for Skill Matching
synonym_dict = {
    "machine learning": ["ml", "deep learning", "artificial intelligence"],
    "data analysis": ["data analytics", "business intelligence"],
    "nlp": ["natural language processing"],
    "sql": ["structured query language", "mysql", "postgresql", "oracle sql", "ms sql", "sqlite", "pl/sql"],
    "c++": ["c plus plus", "cpp", "c++"],
    "web development": ["web dev", "frontend", "backend", "full-stack", "web development"]
}

# Skill Headings for detecting skill sections
skill_headings = [
    "skills",
    "technical skills",
    "soft skills",
    "additional skills",
    "professional skills",
    "programming skills",
    "programming languages",
    "languages",
    "tools",
    "technologies",
    "expertise",
    "proficiencies",
    "side skills",
    "key skills",
    "strengths",
    "technical proficiency"
]

# Set your Poppler path (for Windows, adjust as needed)
poppler_path = r"C:\Program Files\poppler-24.08.0\Library\bin"

# Extract Text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        if text.strip():
            print("[INFO] Text extracted using PyPDF2.")
            return text.lower().translate(str.maketrans('', '', string.punctuation.replace('+', '')))
    except Exception as e:
        print(f"[WARNING] Error with PyPDF2: {e}")

    # Fallback to OCR
    try:
        print("[INFO] Trying OCR fallback...")
        pages = convert_from_path(pdf_path, 300, poppler_path=poppler_path)
        for page in pages:
            text += pytesseract.image_to_string(page) + "\n"
        return text.lower().translate(str.maketrans('', '', string.punctuation.replace('+', '')))
    except Exception as e:
        print(f"[ERROR] OCR fallback failed: {e}")
        return ""

# Extract Text from DOCX
def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text.lower()

def extract_skill_section(text):
    """
    Find and return skill-related section from resume text.
    Only capture lines after skill headings like 'Technical Skills', 'Soft Skills', etc.
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    skill_section = []
    capture = False
    for line in lines:
        line_lower = line.lower()
        if any(heading in line_lower for heading in skill_headings):
            capture = True
            continue  # skip the heading line itself
        elif capture:
            # Stop if new major section like Experience, Education starts
            if len(line) == 0 or any(x in line_lower for x in ["experience", "education", "project", "certification", "profile summary", "summary"]):
                break
            skill_section.append(line)

    return ' '.join(skill_section)

# Extract Resume Information
def extract_resume_info(text, job_keywords, filename=""):
    name = extract_name(text, filename)

    # Email extraction
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group(0) if email_match else "Not Found"

    phone_match = re.search(r"(\+92|0092)?[-\s]?\d{3}[-\s]?\d{7}", text)
    phone = phone_match.group(0) if phone_match else "Not Found"

    address_match = re.search(
        r"(House|Flat|Apartment|Plot)\s*(No\.?|#)?\s*\d+[-\w]*,?\s*(Street|Block|Sector|Phase)?\s*\d*[-\w]*,?.*?(Karachi|Lahore|Islamabad|Rawalpindi|Peshawar|Multan|Quetta|Hyderabad|Faisalabad)",
        text,
        re.IGNORECASE
    )
    address = address_match.group(0) if address_match else "Not Found"

    # ✨ Use only skill section now
    skill_text = extract_skill_section(text)

    skills = []
    for s in job_keywords:
        pattern = r"\b" + re.escape(s.lower()) + r"\b"
        if re.search(pattern, skill_text.lower()):
            skills.append(s)

    return name, email, phone, address, skills

# === Name Extraction Functions ===

def extract_name(text, filename=""):
    """
    1. Try full filename match inside text.
    2. Try first name + next word from text.
    3. Try pattern-based extraction.
    4. Fallback: filename cleaned first part or "Name Not Found".
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

    # 4. Last fallback
    return clean_filename if clean_filename else "Name Not Found"

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

# Normalize Skills using Synonyms
def normalize_skills(resume_skills):
    normalized_resume_skills = set()
    unknown_skills = set()

    for skill in resume_skills:
        skill_lower = skill.lower()
        matched = False
        for key, synonyms in synonym_dict.items():
            if skill_lower == key or skill_lower in synonyms:
                normalized_resume_skills.add(key)
                matched = True
                break
            if not matched:
                for synonym in synonyms + [key]:
                    if fuzz.partial_ratio(skill_lower, synonym) >= 80:
                        normalized_resume_skills.add(key)
                        matched = True
                        break
            if matched:
                break
        if not matched:
            normalized_resume_skills.add(skill_lower)
            unknown_skills.add(skill_lower)  # 👈 catch unknown skills here!

    # 🔥 Save unknown/misspelled skills to a file
    if unknown_skills:
        with open("misspelled_skills_log.txt", "a") as f:
            for s in unknown_skills:
                f.write(s + "\n")

    return normalized_resume_skills
# Generate Matched vs Missing Visualization
def generate_visualization(matched_skills, missing_skills, match_percentage, filename_prefix):
    skills = list(matched_skills) + list(missing_skills)
    presence = [1] * len(skills)
    colors = ["green"] * len(matched_skills) + ["red"] * len(missing_skills)

    plt.figure(figsize=(8, 5))
    plt.bar(skills, presence, color=colors)
    plt.xlabel("Skills")
    plt.ylabel("Presence")
    plt.title("Matched & Missing Skills")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"static/{filename_prefix}_bar_chart.png")
    plt.close()

    plt.figure(figsize=(5, 5))
    plt.pie([match_percentage, 100 - match_percentage],
            labels=["Matched", "Not Matched"],
            colors=["green", "red"],
            autopct="%1.1f%%")
    plt.title("Resume Match Percentage")
    plt.savefig(f"static/{filename_prefix}_pie_chart.png")
    plt.close()

# Generate Top Candidate Ranking Chart
def generate_ranking_chart(candidate_results, filename="static/top_candidates.png"):
    names = [c['name'] for c in candidate_results]
    scores = [c['percentage'] for c in candidate_results]

    plt.figure(figsize=(10, 6))
    bars = plt.barh(names, scores, color="skyblue")
    plt.xlabel("Match Percentage")
    plt.title("Top Candidates Ranked by Resume Match")

    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1, bar.get_y() + bar.get_height() / 2, f'{width:.1f}%', va='center')

    plt.xlim(0, 100)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

# Process Multiple Resumes
def process_multiple_resumes(resumes, job_keywords):
    results = []
    for resume_path in resumes:
        print(f"[INFO] Processing resume: {resume_path}")
        if resume_path.endswith(".pdf"):
            resume_text = extract_text_from_pdf(resume_path)
        elif resume_path.endswith(".docx"):
            resume_text = extract_text_from_docx(resume_path)
        else:
            print("[ERROR] Unsupported file type.")
            continue

        if not resume_text.strip():
            print("[WARNING] Resume text is empty after extraction!")
            continue

        filename = os.path.basename(resume_path)
        name, email, phone, address, resume_skills = extract_resume_info(resume_text, job_keywords, filename=filename)
        normalized_resume_skills = normalize_skills(resume_skills)

        final_matched_skills = set()
        for job_skill in job_keywords:
            result = process.extractOne(job_skill, normalized_resume_skills)
            if result:
                match, score = result
                if score >= 85:
                    final_matched_skills.add(job_skill)

        match_percentage = (len(final_matched_skills) / len(job_keywords)) * 100 if job_keywords else 0
        missing_skills = set(job_keywords) - final_matched_skills

        filename_prefix = os.path.splitext(os.path.basename(resume_path))[0]
        generate_visualization(final_matched_skills, missing_skills, match_percentage, filename_prefix)

        results.append({
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "skills": final_matched_skills,
            "percentage": match_percentage
        })

    return results

# Flask Route
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_keywords = request.form["job_description"].lower().split(",")
        job_keywords = [k.strip() for k in job_keywords if k.strip()]
        
        if not job_keywords:
            return "Please enter at least one job skill!"

        files = request.files.getlist("resumes")
        file_paths = []

        for file in files:
            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)
            file_paths.append(filepath)

        results = process_multiple_resumes(file_paths, job_keywords)

        # Clean up the uploaded files
        for filepath in file_paths:
            os.remove(filepath)

        sorted_results = sorted(results, key=lambda x: x["percentage"], reverse=True)
        top_candidates = sorted_results[:10]

        generate_ranking_chart(top_candidates)

        return render_template("result.html", candidates=top_candidates)

    return render_template("index.html")

# Run the App
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    app.run(debug=True)