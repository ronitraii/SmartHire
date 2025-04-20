from flask import Flask, render_template, request
import re
import os
import matplotlib.pyplot as plt
import PyPDF2
import docx
from fuzzywuzzy import process

app = Flask(__name__)

# Synonym Dictionary for Skill Matching
synonym_dict = {
    "machine learning": ["ml", "deep learning", "artificial intelligence"],
    "data analysis": ["data analytics", "business intelligence"],
    "nlp": ["natural language processing"],
    "sql": ["structured query language"]
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

# Function to Extract Information from Resume Text
def extract_resume_info(text):
    name_match = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*)", text)
    name = name_match.group(0) if name_match else "Not Found"

    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    email = email_match.group(0) if email_match else "Not Found"

    phone_match = re.search(r"\+?\d[\d -]{8,12}\d", text)
    phone = phone_match.group(0) if phone_match else "Not Found"

    address_match = re.search(r"\d{1,5}\s\w+\s\w+", text)
    address = address_match.group(0) if address_match else "Not Found"

    words = re.findall(r"\b\w+\b", text)
    skills = set(words)

    return name, email, phone, address, skills

# Function to Normalize Resume Skills using Synonyms
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

# Function for Fuzzy Matching
def fuzzy_match(skill, job_keywords, threshold=80):
    match, score = process.extractOne(skill, job_keywords)
    return match if score >= threshold else None

# Function to Process Resume & Match with Job Description
def process_resume(resume_path, job_keywords):
    if resume_path.endswith(".pdf"):
        resume_text = extract_text_from_pdf(resume_path)
    elif resume_path.endswith(".docx"):
        resume_text = extract_text_from_docx(resume_path)
    else:
        return None, None, None, None, None, None, None
    
    name, email, phone, address, resume_skills = extract_resume_info(resume_text)
    normalized_resume_skills = normalize_skills(resume_skills)
    final_matched_skills = set()

    for skill in normalized_resume_skills:
        best_match = fuzzy_match(skill, job_keywords)
        if best_match:
            final_matched_skills.add(best_match)

    match_percentage = (len(final_matched_skills) / len(job_keywords)) * 100
    missing_skills = set(job_keywords) - final_matched_skills

    # Generate Visualization
    generate_visualization(final_matched_skills, missing_skills, match_percentage)

    return name, email, phone, address, final_matched_skills, match_percentage, missing_skills

# Function to Generate Bar & Pie Charts (Without NumPy)
def generate_visualization(matched_skills, missing_skills, match_percentage):
    skills = list(matched_skills) + list(missing_skills)
    presence = [1] * len(skills)  # Replaces np.ones()

    colors = ["green"] * len(matched_skills) + ["red"] * len(missing_skills)

    # Bar Chart
    plt.figure(figsize=(8, 5))
    plt.bar(skills, presence, color=colors)
    plt.xlabel("Skills")
    plt.ylabel("Presence")
    plt.title("Matched & Missing Skills")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("static/bar_chart.png")
    plt.close()

    # Pie Chart
    plt.figure(figsize=(5, 5))
    plt.pie([match_percentage, 100 - match_percentage], labels=["Matched", "Not Matched"], colors=["green", "red"], autopct="%1.1f%%")
    plt.title("Resume Match Percentage")
    plt.savefig("static/pie_chart.png")
    plt.close()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        job_keywords = request.form["job_description"].lower().split(",")
        file = request.files["resume"]
        if file:
            filepath = os.path.join("uploads", file.filename)
            file.save(filepath)
            name, email, phone, address, matched_skills, match_percentage, missing_skills = process_resume(filepath, job_keywords)
            os.remove(filepath)  
            return render_template("result.html", name=name, email=email, phone=phone, address=address, skills=matched_skills, percentage=match_percentage)
    return render_template("index.html")

if __name__ == "__main__":
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
    app.run(debug=True)
