#!/bin/bash
# Validate JSON examples in MIP files

echo "Validating JSON examples in MIP files..."
for file in *.md; do
  if [ -f "$file" ]; then
    echo "Checking $file..."
    # Extract JSON code blocks and validate
    grep -A 1000 '```json' "$file" | grep -B 1000 '```' | grep -v '```' | python3 -m json.tool > /dev/null 2>&1
    if [ $? -eq 0 ]; then
      echo "  ✓ Valid JSON found"
    fi
  fi
done
