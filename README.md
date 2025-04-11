CodeRevamp AI
=============

**CodeRevamp AI** is an innovative, AI-powered code refactoring assistant that revolutionizes the way developers enhance code quality. By seamlessly integrating with GitHub and leveraging the power of OpenAI's GPT-4, CodeRevamp AI not only cleans up your code but also provides insightful explanations—focusing on readability, efficiency, and best practices specific to the language—to help teams build more maintainable and efficient software.

Why CodeRevamp AI?
------------------

In today's fast-paced development environments, maintaining high-quality code is critical. CodeRevamp AI is engineered to:

*   **Boost Productivity:** Automatically refactor code, reducing manual code reviews and repetitive tasks.
    
*   **Enhance Code Quality:** Improve readability, efficiency, and adherence to best practices tailored to each programming language.
    
*   **Empower Developers:** Provide detailed, human-readable explanations for every change, highlighting improvements in readability, efficiency, and best practices specific to {language}.
    
*   **Integrate Seamlessly:** Connect directly with GitHub, making it a natural part of your development workflow.
    

Key Features
------------

*   **GitHub Integration:**Easily connect your GitHub account to analyze repositories and identify code that needs improvement.
    
*   **Automated Code Refactoring:**Leverage AI to automatically refactor code while preserving original functionality, reducing technical debt and improving maintainability.
    
*   **Insightful Explanations:**Receive comprehensive explanations for every refactoring change, focusing on improvements in readability, efficiency, and best practices specific to the language you’re working with.
    
*   **Batch Processing:**Refactor individual files or entire directories (including nested folders) with a single click—ideal for large-scale codebases.
    
*   **Modern, User-Friendly Interface:**Enjoy a sleek, dark-themed interface built with Flask and Tailwind CSS, designed for an intuitive and efficient user experience.
    

Technical Overview
------------------

*   **Backend:**
    
    *   Built with Python and Flask for a robust, scalable API.
        
    *   Integrates with the OpenAI API (GPT-4) to drive code refactoring and detailed explanations.
        
    *   Utilizes the GitHub API for secure and efficient repository scanning.
        
*   **Frontend:**
    
    *   Crafted with HTML, CSS (Tailwind CSS), and JavaScript.
        
    *   Responsive design ensures smooth performance across devices.
        
    *   Interactive file explorer and code comparison views for a seamless user experience.
        
*   **Deployment:**
    
    *   Deployed on Render using Gunicorn as a production-ready WSGI server.
        
    *   Secure environment variables for API keys and sensitive configuration settings.
        

Getting Started
---------------

### Prerequisites

*   **Local Development:**Python 3.8+ and pip are required.
    
*   **Hosting:**A Render account to deploy the application.
    

### Installation

1. **Clone the Repository:**

```bash
   git clone https://github.com/mgulati3/code-revamp-ai.git
   cd code-revamp-ai
```

2. **Set Up a Virtual Environment & Install Dependencies: bash Copy:**

```bash
   python -m venv venv
   source venv/bin/activate  # For Windows, use: venv\Scripts\activate
   pip install -r requirements.txt
```

3. **Configure Environment Variables:**

   Create a .env file in the project root with the following:
       GITHUB_CLIENT_ID=your_github_client_id
       GITHUB_CLIENT_SECRET=your_github_client_secret
       OPENAI_API_KEY=your_openai_api_key
       SECRET_KEY=your_flask_secret_key

### Running Locally

**Start the development server with:**

```bash
   flash run
```


## Usage

### Connect to GitHub
Click the **"Connect with GitHub"** button on the homepage to authenticate using GitHub OAuth.  
Ensure your GitHub OAuth app’s callback URL is set to:  
`https://coderevamp-ai.onrender.com/github-callback`

### Select a Repository
After authentication, your dashboard will display your repositories. Click on a repository to view its contents.

### Refactor Code
- Open a file or folder to analyze.
- Click **"Refactor This Code"** to send the code to the OpenAI API for refactoring.
- Once complete, the tool displays the refactored code along with detailed explanations focusing on **readability, efficiency, and best practices specific to {language}**.

### Download Refactored Files
If you refactor a folder, you can download the entire set of refactored files along with explanations in a zip archive.


## Conclusion

**CodeRevamp AI** embodies a cutting-edge solution designed for modern development workflows. It not only streamlines the refactoring process but also educates developers by explaining improvements in detail—focusing on **readability, efficiency, and best practices specific to the language**. This project is a standout addition to any tech portfolio, demonstrating the innovative application of AI to solve real-world software engineering challenges.






