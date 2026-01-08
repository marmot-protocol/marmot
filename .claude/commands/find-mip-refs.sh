#!/bin/bash
# Find all references to MIPs across the codebase

echo "Finding MIP references..."
grep -r "MIP-[0-9][0-9]" *.md threat_model.md data_flows.md 2>/dev/null | grep -v "^Binary" | sort | uniq
