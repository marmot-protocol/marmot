#!/bin/bash
# Validate JSON examples in MIP files

echo "Validating JSON examples in MIP files..."

for file in *.md; do
  if [ -f "$file" ]; then
    echo "Checking $file..."

    valid=0
    invalid=0

    # Extract and validate each JSON block individually
    awk '
      /```json/ { in_block=1; block=""; next }
      in_block && /```/ {
        in_block=0
        if (block != "") {
          cmd = "python3 -m json.tool > /dev/null 2>&1"
          print block | cmd
          status = close(cmd)
          if (status == 0) {
            valid++
          } else {
            invalid++
            print "  ✗ Invalid JSON block found" > "/dev/stderr"
          }
          block=""
        }
        next
      }
      in_block { block = block $0 "\n" }
      END {
        if (valid > 0) print "  ✓ Found " valid " valid JSON block(s)"
        if (invalid > 0) print "  ✗ Found " invalid " invalid JSON block(s)"
      }
    ' "$file"
  fi
done
