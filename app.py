# AI-Powered Code Refactoring Assistant
# app.py - Main Flask Application

import os
import requests
import base64
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI  # Updated import statement

# Load environment variables
load_dotenv()

# Optionally remove proxy settings if they're causing issues
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get("SECRET_KEY", "default-secret-key")

# GitHub API Configuration
GITHUB_API_URL = "https://api.github.com"
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# OpenAI Configuration
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  # Create client instance

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/github-login')
def github_login():
    """Redirect user to GitHub for authentication"""
    if not GITHUB_CLIENT_ID:
        return "Error: GitHub Client ID is not set", 500
    return redirect(f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&scope=repo")


@app.route('/github-callback')
def github_callback():
    """Handle GitHub OAuth callback"""
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "GitHub authentication failed"}), 400
    
    # Exchange code for access token
    response = requests.post(
        "https://github.com/login/oauth/access_token",
        data={
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code
        },
        headers={"Accept": "application/json"}
    )
    
    data = response.json()
    if "access_token" not in data:
        return jsonify({"error": "Failed to get GitHub access token"}), 400
    
    # Store token in session
    session['github_token'] = data['access_token']
    
    # Get user info
    user_response = requests.get(
        f"{GITHUB_API_URL}/user",
        headers={"Authorization": f"token {data['access_token']}"}
    )
    user_data = user_response.json()
    session['github_user'] = user_data.get('login')
    
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    """Display user's repositories"""
    if 'github_token' not in session:
        return redirect('/github-login')
    
    # Get user's repositories
    repos_response = requests.get(
        f"{GITHUB_API_URL}/user/repos",
        headers={"Authorization": f"token {session['github_token']}"}
    )
    
    repos = repos_response.json()
    return render_template('dashboard.html', repos=repos, user=session['github_user'])

@app.route('/analyze/<owner>/<repo>')
def analyze_repo(owner, repo):
    """Display repository files for analysis"""
    if 'github_token' not in session:
        return redirect('/github-login')
    
    # Get repository contents (root directory)
    contents_response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents",
        headers={"Authorization": f"token {session['github_token']}"}
    )
    
    if contents_response.status_code != 200:
        return jsonify({"error": "Failed to fetch repository contents"}), 400
    
    contents = contents_response.json()
    return render_template('repo_analyzer.html', owner=owner, repo=repo, contents=contents)

@app.route('/get-file-content')
def get_file_content():
    """Get content of a file from GitHub"""
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    file_path = request.args.get('path')
    owner = request.args.get('owner')
    repo = request.args.get('repo')
    
    if not all([file_path, owner, repo]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Get file content
    file_response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{file_path}",
        headers={"Authorization": f"token {session['github_token']}"}
    )
    
    if file_response.status_code != 200:
        return jsonify({"error": "Failed to fetch file content"}), 400
    
    file_data = file_response.json()
    if file_data.get('type') != 'file':
        return jsonify({"error": "Path does not point to a file"}), 400
    
    # Decode content
    content = base64.b64decode(file_data.get('content')).decode('utf-8')
    
    return jsonify({"content": content, "path": file_path})

@app.route('/refactor-code', methods=['POST'])
def refactor_code():
    """Use OpenAI to refactor code"""
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    code = data.get('code')
    language = data.get('language', 'python')  # Default to Python
    
    if not code:
        return jsonify({"error": "No code provided"}), 400
    
    try:
        # First API call to get refactored code
        print(f"Sending refactoring request for {language} code to OpenAI...")
        response = client.chat.completions.create(
            model="gpt-4",  # Use GPT-4 for code refactoring
            messages=[
                {
                    "role": "system",
                    "content": f"You are an expert code refactorer. Refactor the following {language} code to make it cleaner, more efficient, and follow best practices. Maintain the exact same functionality. Return only the refactored code without additional explanations."
                },
                {"role": "user", "content": code}
            ],
            temperature=0.2  # Lower temperature for more focused output
        )
        
        # Get refactored code
        refactored_code = response.choices[0].message.content
        print("Received refactored code from OpenAI")
        
        # Second API call to get explanation
        print("Sending explanation request to OpenAI...")
        explanation_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code reviewer. Explain the changes made between the original code and the refactored code, focusing on improvements in readability, efficiency, and best practices."
                },
                {
                    "role": "user",
                    "content": f"Original code:\n\n{code}\n\nRefactored code:\n\n{refactored_code}\n\nExplain the key improvements made in the refactored version."
                }
            ],
            temperature=0.7
        )
        
        explanation = explanation_response.choices[0].message.content
        print("Received explanation from OpenAI")
        
        return jsonify({
            "original_code": code,
            "refactored_code": refactored_code,
            "explanation": explanation
        })
    
    except Exception as e:
        print(f"Error in refactor-code: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        return jsonify({"error": str(e)}), 500
    
    
@app.route('/logout')
def logout():
    """Log out user by clearing session"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)