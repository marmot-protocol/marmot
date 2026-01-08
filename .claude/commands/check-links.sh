#!/bin/bash
# Check for broken internal links in markdown files

echo "Checking for broken internal links..."
for file in *.md; do
  if [ -f "$file" ]; then
    echo "Checking links in $file..."
    # Extract markdown links and check if target exists
    grep -oP '\[.*?\]\([^)]+\)' "$file" | sed 's/.*(\(.*\))/\1/' | while read link; do
      if [[ $link == *.md ]] && [ ! -f "$link" ]; then
        echo "  ✗ Broken link: $link"
      fi
    done
  fi
done
