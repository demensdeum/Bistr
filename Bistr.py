import os
import requests
import argparse
import time
import json
import tempfile
import sys

SAVE_STATE_FILE = os.path.join(tempfile.gettempdir(), "source_code_analysis_state.json")
time_differences = []
analyzed_files = []

def load_save_state(target_directory):
    if os.path.exists(SAVE_STATE_FILE):
        print(f"Loading save state from: {SAVE_STATE_FILE}")
        with open(SAVE_STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
            if target_directory in state_data:
                return state_data[target_directory]
    return None

def save_state(target_directory, pending_files, context, model):
    state_data = {}
    if os.path.exists(SAVE_STATE_FILE):
        with open(SAVE_STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

    state_data[target_directory] = {
        "pending_files": pending_files,
        "context": context,
        "model": model
    }

    with open(SAVE_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state_data, f, indent=4)
    print(f"State saved to: {SAVE_STATE_FILE}")

def askOllama(prompt, model, context):
    base_url = 'http://localhost:11434'
    endpoint = '/api/generate'

    payload = {
        "model": model,
        "stream": False,
        "prompt": prompt.strip(),
        "context": context
    }
    response = requests.post(base_url + endpoint, json=payload)
    if response.status_code == 200:
        answer = response.json()
        return {"text": answer.get("response"), "context": answer.get("context")}
    else:
        print(f"ollama error: {response}; {response.content}")
        exit(1)

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"

def save_summary_as_html(output_file, analyzed_files, model, research="No research"):
    """Creates an HTML table summarizing the analysis results."""
    with open(output_file, 'w', encoding='utf-8') as html_file:
        html_file.write(f"""
        <html>
        <head>
            <style>
                table {{
                    border-collapse: collapse;
                    width: 100%;
                    border: 1px solid black;
                }}
                table td {{
                    border: 1px solid black;                    
                }}
                th, td {{
                    border: 1px solid black;
                    text-align: left;
                    padding: 8px;
                }}
                th {{
                    background-color: #f2f2f2;
                }}
            </style>
        </head>
        <body>
            <h1>Source Code Analysis Summary</h1>
            <p><strong>Model Used:</strong> {model}</p>
            <p><strong>Research Query:</strong> {research}</p>
            <table>
                <tr>
                    <th>File</th>
                    <th>Relevance</th>
                    <th>Reason</th>
                </tr>
        """)

        for file_data in analyzed_files:
            html_file.write(f"""
                <tr>
                    <td>{file_data['file']}</td>
                    <td>{file_data['relevance']}%</td>
                    <td>{file_data['reason']}</td>
                </tr>
            """)

        html_file.write("""
            </table>
        </body>
        </html>
        """)

def analyze_file_with_context(file_path, model, context, output_html=None, research=None):
    """Analyzes a single file and updates the context."""
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    source_code_path = os.path.basename(file_path)
    if research:
        jsonExample = """
        {
            "relevance": 0, // relevance to question of research from 0-100%
            "reason" : "Reasoning text" // reasoning text why it's relevance to question in research, show exact related code snippets
        }
        """
        researchPrompt = f"\nCan you answer this question \"{research}\"? Is it in this code? Answer in json format\n For example: {jsonExample}\n"
    else:
        researchPrompt = ""
    prompt = f"Analyze the following source code from {source_code_path}:\n\n{code}\n\n{researchPrompt}"
    start_time = time.time()
    response = askOllama(prompt, model, context)
    elapsed_time = time.time() - start_time

    time_differences.append(elapsed_time)

    if response:
        try:
            response_data = json.loads(response["text"])
        except:
            return None
        
        analyzed_files.append({
                "file": os.path.basename(file_path),
                "relevance": response_data.get("relevance", 0),
                "reason": response_data.get("reason", "No reason provided")
            })
        if output_html:
            save_summary_as_html(output_html, analyzed_files, model, research)
        return response["context"]
    else:
        print(f"Failed to get response for {source_code_path}")
        return context
    
def build_context_from_directory(directory, model, state, is_resume, output_html=None, research=None):
    context = state.get("context", [])
    pending_files = state.get("pending_files", [])
    total_files = len(pending_files)
    analyzed_files = []

    if is_resume:
        print(f"Resuming analysis for {total_files} files in {directory}")
    else:
        print(f"Starting new analysis for directory {directory}")

    for idx, file_path in enumerate(pending_files[:], start=1):
        print("")
        progress = int((idx / total_files) * 100)
        print(f"Analyzing: {file_path} {progress}%")
        result = None
        while result == None:
            result = analyze_file_with_context(file_path, model, context, output_html, research)
        pending_files.remove(file_path)
        save_state(directory, pending_files, context, model)
        analyzed_files.append(os.path.basename(file_path))
        avg_time_per_file = sum(time_differences) / len(time_differences)
        remaining_files = total_files - idx
        estimated_remaining_time = avg_time_per_file * remaining_files
        if len(time_differences) >= 4:
            print(f"Estimated time remaining: {format_time(estimated_remaining_time)}")
        else:
            print(f"Pending time estimation")

    return context

def interactive_question_answering(context, model):
    print("You can ask questions about the codebase. Type 'bye' to finish.")
    while True:
        question = input("Enter your question (or 'bye' to finish): ")
        if question.lower() == 'bye':
            break
        response = askOllama(question, model, context)
        if response:
            print("Response:")
            print(response["text"])
            context = response["context"]
        else:
            print("Failed to get a response.")

def sourceCodeAnalysis(directory, model, extensions=None, output_html=None, research=None):
    if extensions is None:
        extensions = ['.py', '.cpp', '.h', '.java', '.js', '.html', '.css']

    abs_directory = os.path.abspath(directory)
    state = load_save_state(abs_directory)

    should_resume = False

    while True:
        if state:
            should_resume = input(f"A previous analysis state was found for {abs_directory}. Do you want to resume? (Y/n): ").strip().lower()

            if should_resume == "y":
                saved_model = state.get("model")
                if saved_model != model:
                    print(f"Error: The saved model '{saved_model}' does not match the current model '{model}'. Exiting.")
                    sys.exit(1)
                break

            elif should_resume == "n":
                state = {"pending_files": get_files_list(abs_directory, extensions), "context": [], "model": model}
                break

            elif len(should_resume) < 1:
                should_resume = "y"
                break

    context = build_context_from_directory(abs_directory, model, state, should_resume == "y", output_html=output_html, research=research)
    interactive_question_answering(context, model)

def get_files_list(directory, extensions):
    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_list.append(os.path.join(root, file))
    return file_list

def main():
    parser = argparse.ArgumentParser(description="Analyze source code and interact with Ollama.")
    parser.add_argument("directory", help="Path to the source code directory to analyze.")
    parser.add_argument("--model", required=True, help="Model to use for analysis.")
    parser.add_argument("--extensions", nargs="*", default=['.py', '.cpp', '.h', '.java', '.js', '.html', '.css'],
                        help="File extensions to analyze (space-separated).")
    parser.add_argument("--output-html", required=True, help="Path to save the HTML summary.")
    parser.add_argument("--research", help="Search for one particular answer in codebase, then stop")

    args = parser.parse_args()
    sourceCodeAnalysis(args.directory, model=args.model, extensions=args.extensions, output_html=args.output_html, research=args.research)

if __name__ == "__main__":
    main()
