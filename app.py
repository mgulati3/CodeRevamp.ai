# app.py - Main Flask Application

import os
import requests
import base64
import json
import zipfile
import io
import time
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI  

# To store large data/ cookie 
refactor_results_storage = {}


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
    
    # Determine language from file extension
    language = get_language_from_file_path(file_path)
    
    return jsonify({"content": content, "path": file_path, "language": language})

@app.route('/get-folder-contents')
def get_folder_contents():
    """
    Get contents of a folder from GitHub.
    This endpoint now returns both code files and subdirectories so that the UI
    can display nested folders as well.
    """
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    folder_path = request.args.get('path', '')
    owner = request.args.get('owner')
    repo = request.args.get('repo')
    
    if not all([owner, repo]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    # Get folder content
    folder_response = requests.get(
        f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{folder_path}",
        headers={"Authorization": f"token {session['github_token']}"}
    )
    
    if folder_response.status_code != 200:
        return jsonify({"error": "Failed to fetch folder contents"}), 400
    
    contents = folder_response.json()
    
    # If it's not a list, it's not a folder
    if not isinstance(contents, list):
        return jsonify({"error": "Path does not point to a folder"}), 400
    
    # Separate code files and directories
    files = [item for item in contents if item['type'] == 'file' and is_code_file(item['name'])]
    dirs = [item for item in contents if item['type'] == 'dir']
    
    return jsonify({"folder_path": folder_path, "files": files, "dirs": dirs})

@app.route('/refactor-code', methods=['POST'])
def refactor_code():
    """Use OpenAI to refactor code"""
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    code = data.get('code')
    language = data.get('language', 'python')  # Get language from request
    
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
                    "content": f"You are an expert {language} developer tasked with refactoring code. Refactor the following {language} code to make it cleaner, more efficient, and follow best practices for {language}. Maintain the exact same functionality. Return only the refactored code without additional explanations."
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
                    "content": f"You are an expert {language} code reviewer. Explain the changes made between the original code and the refactored code, focusing on improvements in readability, efficiency, and best practices specific to {language}."
                },
                {
                    "role": "user",
                    "content": f"Original {language} code:\n\n{code}\n\nRefactored {language} code:\n\n{refactored_code}\n\nExplain the key improvements made in the refactored version."
                }
            ],
            temperature=0.7
        )
        
        explanation = explanation_response.choices[0].message.content
        print("Received explanation from OpenAI")
        
        return jsonify({
            "original_code": code,
            "refactored_code": refactored_code,
            "explanation": explanation,
            "language": language
        })
    
    except Exception as e:
        print(f"Error in refactor-code: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        return jsonify({"error": str(e)}), 500

# Helper function to recursively fetch all code files in a folder (including nested folders)
def get_all_code_files(owner, repo, folder_path, token):
    files = []
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{folder_path}"
    response = requests.get(url, headers={"Authorization": f"token {token}"})
    if response.status_code != 200:
        print(f"Failed to fetch contents for {folder_path}")
        return files
    items = response.json()
    for item in items:
        if item['type'] == 'file' and is_code_file(item['name']):
            files.append(item)
        elif item['type'] == 'dir':
            # Recursively fetch files in subdirectory
            files.extend(get_all_code_files(owner, repo, item['path'], token))
    return files

@app.route('/refactor-folder', methods=['POST'])
def refactor_folder():
    """Refactor all code files in a folder (including nested folders)"""
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    data = request.json
    folder_path = data.get('folder_path', '')
    owner = data.get('owner')
    repo = data.get('repo')
    
    if not all([owner, repo, folder_path]):
        return jsonify({"error": "Missing required parameters"}), 400
    
    try:
        token = session['github_token']
        # Recursively get all code files in the selected folder
        all_files = get_all_code_files(owner, repo, folder_path, token)
        results = []
        
        # Process each file for refactoring
        for file_info in all_files:
            file_path = file_info['path']
            file_response = requests.get(
                f"{GITHUB_API_URL}/repos/{owner}/{repo}/contents/{file_path}",
                headers={"Authorization": f"token {token}"}
            )
            
            if file_response.status_code != 200:
                print(f"Failed to fetch content for {file_path}")
                continue
            
            file_data = file_response.json()
            try:
                content = base64.b64decode(file_data.get('content')).decode('utf-8')
            except Exception as e:
                print(f"Error decoding content for {file_path}: {str(e)}")
                continue
            
            language = get_language_from_file_path(file_path)
            
            try:
                # Refactor code using OpenAI
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert {language} developer tasked with refactoring code. Refactor the following {language} code to make it cleaner, more efficient, and follow best practices for {language}. Maintain the exact same functionality. Return only the refactored code without additional explanations."
                        },
                        {"role": "user", "content": content}
                    ],
                    temperature=0.2
                )
                
                refactored_code = response.choices[0].message.content
                
                explanation_response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert {language} code reviewer. Explain the changes made between the original code and the refactored code, focusing on improvements in readability, efficiency, and best practices specific to {language}."
                        },
                        {
                            "role": "user",
                            "content": f"Original {language} code:\n\n{content}\n\nRefactored {language} code:\n\n{refactored_code}\n\nExplain the key improvements made in the refactored version."
                        }
                    ],
                    temperature=0.7
                )
                explanation = explanation_response.choices[0].message.content
                
                results.append({
                    "file_path": file_path,
                    "language": language,
                    "original_code": content,
                    "refactored_code": refactored_code,
                    "explanation": explanation
                })
                # Add a small delay to avoid hitting API rate limits
                time.sleep(0.5)
            except Exception as e:
                print(f"Error refactoring {file_path}: {str(e)}")
                continue
        
        # Create a unique batch ID for this refactoring process
        batch_id = f"refactor_{int(time.time())}"
        refactor_results_storage[batch_id] = results
        
        return jsonify({
            "status": "success",
            "message": f"Refactored {len(results)} files",
            "batch_id": batch_id,
            "results": results
        })
    
    except Exception as e:
        print(f"Error in refactor-folder: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/download-refactored-files/<batch_id>')
def download_refactored_files(batch_id):
    """Download all refactored files as a zip archive with preserved folder structure"""
    if 'github_token' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Retrieve results from the global dictionary
    if batch_id not in refactor_results_storage:
        return jsonify({"error": "Refactoring results not found"}), 404

    results = refactor_results_storage[batch_id]
    # Create a zip file in memory, preserving folder structure
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for result in results:
            file_path = result['file_path']
            refactored_code = result['refactored_code']
            
            # Add the refactored file using its full path
            zf.writestr(file_path, refactored_code)
            
            # Also add a markdown file with the explanation
            explanation_file = f"{file_path}_explanation.md"
            explanation_content = f"# Refactoring Explanation for {file_path}\n\n{result['explanation']}"
            zf.writestr(explanation_file, explanation_content)
    
    memory_file.seek(0)
    
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'refactored_code_{batch_id}.zip'
    )

def get_language_from_file_path(file_path):
    """Determine language from file extension"""
    language = "python"  # Default
    if file_path:
        file_extension = file_path.split('.')[-1].lower() if '.' in file_path else ""
        if file_extension in ['js', 'jsx']:
            language = 'javascript'
        elif file_extension in ['ts', 'tsx']:
            language = 'typescript'
        elif file_extension in ['java']:
            language = 'java'
        elif file_extension in ['rb']:
            language = 'ruby'
        elif file_extension in ['cpp', 'cc', 'cxx', 'h', 'hpp']:
            language = 'C++'
        elif file_extension in ['cs']:
            language = 'C#'
        elif file_extension in ['go']:
            language = 'go'
        elif file_extension in ['php']:
            language = 'php'
        elif file_extension in ['swift']:
            language = 'swift'
        elif file_extension in ['kt', 'kts']:
            language = 'kotlin'
        elif file_extension in ['rs']:
            language = 'rust'
        elif file_extension in ['scala']:
            language = 'scala'
    return language

def is_code_file(filename):
    """Check if a file is likely to be a code file based on its extension"""
    code_extensions = [
        'py', 'js', 'jsx', 'ts', 'tsx', 'java', 'rb', 'cpp', 'cc', 'cxx', 'h', 'hpp',
        'cs', 'go', 'php', 'swift', 'kt', 'kts', 'rs', 'scala', 'c', 'sh', 'pl', 'pm',
        'html', 'css', 'scss', 'sql', 'r', 'm', 'f', 'f90', 'dart'
    ]
    if '.' in filename:
        extension = filename.split('.')[-1].lower()
        return extension in code_extensions
    return False

@app.route('/logout')
def logout():
    """Log out user by clearing session"""
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
