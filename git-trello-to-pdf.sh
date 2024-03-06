#!/bin/bash

# Initialize our own variables
timestamp=$(date +"%Y-%m-%d-%H-%M-%S")
trello_email=""
password=""
repo_dir=""
output_dir=""

# Parse command-line options
while getopts ":e:p:r:o:h" opt; do
  case $opt in
    e)
      trello_email=$OPTARG
      ;;
    p)
      password=$OPTARG
      ;;
    r)
      repo_dir=$OPTARG
      ;;
    o)
      output_dir=$OPTARG
      ;;
    h)
      echo "Usage: git-trello-to-pdf.sh -e EMAIL -p PASSWORD -r REPO_DIR -o OUTPUT_DIR"
      echo
      echo "Options:"
      echo "  -e EMAIL      Your Trello email"
      echo "  -p PASSWORD   Your password"
      echo "  -r REPO_DIR   The git repository directory"
      echo "  -o OUTPUT_DIR The output directory (default: ./output)"
      echo "  -h            Display this help message"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

# If variables are not set, ask for them
if [ -z "$trello_email" ]; then
    read -p "Enter your Trello email: " trello_email
fi
if [ -z "$password" ]; then
    read -sp "Enter your password: " password
    echo
fi
if [ -z "$repo_dir" ]; then
    read -p "Enter the git repository directory: " repo_dir
fi
if [ -z "$output_dir" ]; then
    output_dir=$(pwd)/output/$timestamp
else
    output_dir=$output_dir/$timestamp
fi


create_output_dir() {
    mkdir -p "$1/errors"
    mkdir -p "$1/trello_cards"
}

setup_venv() {
    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
}

get_commit_messages() {
    cd "$1" || exit
    git log --pretty=format:"%s" > "$2/commit_messages.txt"
    echo "Git commit messages have been saved to $2/commit_messages.txt"
}

extract_trello_hashes() {
    pcre2grep --only-matching '(?<=\[t[:-])[a-zA-Z0-9]+(?=\])' "$1/commit_messages.txt" | sort -u > "$1/trello_card_hashes.txt"
    echo "Trello card hashes have been saved to $1/trello_card_hashes.txt"
}

run_trello_to_pdf() {
    python trello_to_pdf.py "$1/trello_card_hashes.txt" -o "$1/trello_cards" > "$1/trello_to_pdf.log"
    grep -E "Card (.*) not found" "$1/trello_to_pdf.log" > "$1/errors/trello_card_not_found.txt"
    grep -E "Card (.*) requires access" "$1/trello_to_pdf.log" > "$1/errors/trello_card_requires_access.txt"
    echo "Trello card details have been saved to $1/trello_cards"
}

create_output_dir() {
    mkdir -p "$1/errors"
    mkdir -p "$1/trello_cards"
}

setup_venv() {
    if [ ! -d .venv ]; then
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
}

get_commit_messages() {
    pushd "$1" || exit
    git log --pretty=format:"%s" > "$2/commit_messages.txt"
    echo "Git commit messages have been saved to $2/commit_messages.txt"
    popd || exit
}

extract_trello_hashes() {
    pcre2grep --only-matching '(?<=\[t[:-])[a-zA-Z0-9]+(?=\])' "$1/commit_messages.txt" | sort -u > "$1/trello_card_hashes.txt"
    echo "Trello card hashes have been saved to $1/trello_card_hashes.txt"
}

run_trello_to_pdf() {
    python -u trello_to_pdf.py -i "$1/trello_card_hashes.txt" -o "$1/trello_cards" -u $2 -p $3 | tee "$1/trello_to_pdf.log"
    grep -E "Card (.*) not found" "$1/trello_to_pdf.log" > "$1/errors/trello_card_not_found.txt"
    grep -E "Card (.*) requires access" "$1/trello_to_pdf.log" > "$1/errors/trello_card_requires_access.txt"
    echo "Trello card details have been saved to $1/trello_cards"
}

# Main script
create_output_dir $output_dir
setup_venv
get_commit_messages $repo_dir $output_dir
extract_trello_hashes $output_dir
run_trello_to_pdf $output_dir $trello_email $password