# Git-Trello-to-PDF

This script extracts Trello card hashes from git commit messages and generates PDFs of the corresponding Trello cards.

## Supported OS

- macOS
- Linux
- BSDs

## Prerequisites

- bash
- Python 3
- git
- pcre2grep

## Usage

1. Clone the repository and navigate to the directory containing the script.

    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2. Run the script with the required options:

    ```bash
    sh git-trello-to-pdf.sh -e EMAIL -p PASSWORD -r REPO_DIR -o OUTPUT_DIR
    ```

    - `-e EMAIL`: Your Trello email
    - `-p PASSWORD`: Your Trello password
    - `-r REPO_DIR`: The git repository directory
    - `-o OUTPUT_DIR`: The output directory (default: ./output)

    If you don't provide these options, the script will prompt you to enter them.

3. The script will create an output directory with the current timestamp, extract Trello card hashes from the git commit messages, and generate PDFs of the Trello cards.

## Output

The script generates the following files in the output directory:

- `commit_messages.txt`: A list of all git commit messages
- `trello_card_hashes.txt`: A list of all extracted Trello card hashes
- `trello_cards`: A directory containing the generated PDFs of the Trello cards
- `errors/trello_card_not_found.txt`: A list of Trello card hashes that could not be found
- `errors/trello_card_requires_access.txt`: A list of Trello card hashes that require access

## Note

The script uses a Python virtual environment to install its dependencies. If you want to use the script in a different Python environment, you'll need to install the dependencies manually.