
# Bistr: Source Code Analysis with Ollama

Bistr is a tool for analyzing source code files in a directory using Ollama, an AI model that interprets and analyzes code. The script recursively processes the files in a given directory, based on their extensions, and uses Ollama for code analysis. It also supports state-saving, allowing you to resume analysis from where you left off.

![Logo](logo.png)

## Features

- **Source Code Analysis:** Analyzes code files in a specified jrectory using Ollama.
- **Context Management:** Tracks the context of previous analyses to improve the quality of responses.
- **State Persistence:** Saves progress, enabling you to resume analysis from the last point.
- **Customizable Extensions:** Specify which file types (extensions) to analyze.

## Requirements

- Python 3.x
- `requests` library (for HTTP requests to Ollama API)
- Ollama model server running locally (`localhost:11434`)
- Python’s `json` and `tempfile` libraries (included in the standard library)

## Installation

1. Clone this repository:
   ```bash
    git clone https://github.com/demensdeum/Bistr
   ```

### Arguments:
- `directory`: Path to the directory containing the source code to analyze.
- `--model`: Model to use for analisis (required).
- `--extensions`: Space-separated list of file extensions to analyze (optional, default: `.py .cpp .h .java .js .html .css`).
- `--output-html`: Path to save the HTML summary.
- `--research`: Search for one particular answer in codebase


### Example:

To analyze Python and C++ files in the `/path/to/code` directory using a model called `code-analyzer`, run:

```bash
python bistr.py /path/to/code --model llama3.1:latest --output-html result.html --research "What is the purpose of this function?"
```

### Resuming Analysis:

If a previous analysis state exists for the directory, you will be prompted whether to resume the analysis. If you choose "n" the analysis will restart from the beginning.