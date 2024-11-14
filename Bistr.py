import os
import requests
import argparse
import time
import json
import tempfile
import sys

SAVE_STATE_FILE = os.path.join(tempfile.gettempdir(), "source_code_analysis_state.json")
time_differences = []

def load_save_state(target_directory):
    """Loads the save state from the file, if it exists."""
    if os.path.exists(SAVE_STATE_FILE):
        print(f"Loading save state from: {SAVE_STATE_FILE}")
        with open(SAVE_STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
            if target_directory in state_data:
                return state_data[target_directory]
    return None

def save_state(target_directory, pending_files, context, model):
    """Saves the current state to the file, including the model name."""
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

def analyze_file_with_context(file_path, model, context):
    """Analyzes a single file and updates the context."""
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()

    source_code_path = os.path.basename(file_path)
    prompt = f"Analyze the following source code from {source_code_path}:\n\n{code}\n\n"
    start_time = time.time()
    response = askOllama(prompt, model, context)
    elapsed_time = time.time() - start_time

    time_differences.append(elapsed_time)

    if response:
        print("")
        print(f"Analysis for {source_code_path}:")
        print(response["text"])
        print(f"Time taken: {format_time(elapsed_time)}")
        return response["context"]
    else:
        print(f"Failed to get response for {source_code_path}")
        return context

def build_context_from_directory(directory, model, state, resume):
    """Builds context by analyzing each file in the specified directory with given extensions."""
    context = state.get("context", [])
    pending_files = state.get("pending_files", [])
    total_files = len(pending_files)

    if resume:
        print(f"Resuming analysis for {total_files} files in {directory}")
    else:
        print(f"Starting new analysis for directory {directory}")

    for idx, file_path in enumerate(pending_files[:], start=1):
        print("")
        progress = int((idx / total_files) * 100)
        print(f"Analyzing: {file_path} {progress}%")
        context = analyze_file_with_context(file_path, model, context)
        pending_files.remove(file_path)
        save_state(directory, pending_files, context, model)
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

def sourceCodeAnalysis(directory, model, extensions=None):
    if extensions is None:
        extensions = ['.py', '.cpp', '.h', '.java', '.js', '.html', '.css']

    abs_directory = os.path.abspath(directory)
    state = load_save_state(abs_directory)

    resume = False

    if state:
        resume = input(f"A previous analysis state was found for {abs_directory}. Do you want to resume? (yes/no): ").strip().lower()

        if resume == "yes":
            saved_model = state.get("model")
            if saved_model != model:
                print(f"Error: The saved model '{saved_model}' does not match the current model '{model}'. Exiting.")
                sys.exit(1)

        else:
            state = {"pending_files": get_files_list(abs_directory, extensions), "context": [], "model": model}
    else:
        state = {"pending_files": get_files_list(abs_directory, extensions), "context": [], "model": model}

    context = build_context_from_directory(abs_directory, model, state, resume == "yes")
    interactive_question_answering(context, model)

def get_files_list(directory, extensions):
    """Generates a list of files to be analyzed."""
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

    args = parser.parse_args()
    sourceCodeAnalysis(args.directory, model=args.model, extensions=args.extensions)

if __name__ == "__main__":
    main()
