#!/bin/bash
# Check for broken internal links in markdown files

echo "Checking for broken internal links..."

# Find all markdown files recursively
find . -name "*.md" -type f | while read file; do
  echo "Checking links in $file..."

  # Extract markdown links and process each one
  grep -oP '\[.*?\]\([^)]+\)' "$file" | sed 's/.*(\(.*\))/\1/' | while read link; do
    # Skip external URLs (http://, https://, mailto:, etc.)
    if [[ "$link" =~ ^(https?|mailto|ftp):// ]]; then
      continue
    fi

    # Strip URL fragments/anchors (e.g., file.md#section -> file.md)
    target_file="${link%%#*}"

    # Handle relative paths
    # Remove ./ prefix if present
    target_file="${target_file#./}"

    # Resolve relative paths
    if [[ "$target_file" == ../* ]]; then
      # For ../ paths, resolve relative to the markdown file's directory
      file_dir=$(dirname "$file")
      resolved_path=$(cd "$file_dir" 2>/dev/null && cd "$(dirname "$target_file")" 2>/dev/null && pwd)/$(basename "$target_file")
      target_file="$resolved_path"
    elif [[ "$target_file" != /* ]]; then
      # Relative path - resolve relative to the markdown file's directory
      file_dir=$(dirname "$file")
      target_file="$file_dir/$target_file"
    fi

    # Normalize path (remove .. and . components)
    target_file=$(echo "$target_file" | sed 's|/\./|/|g' | sed 's|/[^/]*/\.\./|/|g')

    # Check if target file exists
    if [[ "$target_file" == *.md ]] && [ ! -f "$target_file" ]; then
      echo "  ✗ Broken link: $link -> $target_file"
    fi
  done
done
