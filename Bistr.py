import os
import requests
import argparse
import time  # Import the time module for benchmarking

def askOllama(prompt, model, context):
    base_url = 'http://localhost:11434'
    endpoint = '/api/generate'

    prompt = prompt.strip()

    payload = {
        "model": model, 
        "stream": False,                            
        "prompt": prompt,
        "context": context   
    }
    response = requests.post(base_url + endpoint, json=payload)
    if response.status_code == 200:
        answer = response.json()

        text = answer.get("response")
        context = answer.get("context")

        return {"text": text, "context": context}
    else:
        print(f"ollama error: {response}; {response.content}")
        exit(1)

def format_time(seconds):
    """Converts seconds into hours, minutes, and seconds."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours}h {minutes}m {seconds}s"

def analyze_file_with_context(file_path, model, context):
    """Analyzes a single file and updates the context with Ollama's response."""
    start_time = time.time()  # Record start time for benchmarking
    
    with open(file_path, 'r', encoding='utf-8') as f:
        code = f.read()
    
    source_code_path = os.path.basename(file_path)
    print(f"Analyzing: {source_code_path}")
    prompt = f"Analyze the following source code from {source_code_path}:\n\n{code}\n\n"
    
    response = askOllama(prompt, model, context)
    
    end_time = time.time()  # Record end time for benchmarking
    elapsed_time = end_time - start_time  # Calculate elapsed time

    if response:
        print(f"Analysis for {os.path.basename(file_path)}:")
        print(response["text"])
        print(f"Time taken to analyze {source_code_path}: {format_time(elapsed_time)}")
        return response["context"], elapsed_time
    else:
        print(f"Failed to get response for {os.path.basename(file_path)}")
        return context, 0  # Return zero time if analysis failed

def build_context_from_directory(directory, model, extensions):
    """Builds context by analyzing each file in the specified directory with given extensions."""
    context = []
    file_list = []  # List to store file paths
    total_files = 0

    # Gather all files to analyze first
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                file_list.append(file_path)
                total_files += 1

    print(f"Total files to analyze: {total_files}")

    # Now, analyze files and calculate estimated time
    total_time = 0
    for idx, file_path in enumerate(file_list, start=1):
        context, file_time = analyze_file_with_context(file_path, model, context)
        total_time += file_time

        # Estimate the remaining time
        avg_time_per_file = total_time / idx
        remaining_files = total_files - idx
        estimated_remaining_time = avg_time_per_file * remaining_files
        print(f"Estimated time remaining: {format_time(estimated_remaining_time)}")

    return context

def interactive_question_answering(context, model):
    """Prompts the user to ask questions and gets responses from Ollama, one question at a time."""
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
            print("Failed to get a response for this question.")

def sourceCodeAnalysis(directory, model, extensions=None):
    if extensions is None:
        extensions = ['.py', '.cpp', '.h', '.java', '.js', '.html', '.css']
    
    context = build_context_from_directory(directory, model, extensions)
    
    interactive_question_answering(context, model)

def main():
    parser = argparse.ArgumentParser(description="Analyze source code and interact with Ollama.")
    parser.add_argument("directory", help="Path to the source code directory to analyze.")
    parser.add_argument("--model", required=True, help="Model to use for analysis. This is a required argument.")
    parser.add_argument("--extensions", nargs="*", default=['.py', '.cpp', '.h', '.java', '.js', '.html', '.css'],
                        help="File extensions to analyze (space-separated). Default includes '.py', '.cpp', '.h', '.java', '.js', '.html', '.css'.")

    args = parser.parse_args()

    sourceCodeAnalysis(args.directory, model=args.model, extensions=args.extensions)

if __name__ == "__main__":
    main()
