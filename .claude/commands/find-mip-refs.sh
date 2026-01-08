#!/bin/bash
# Find all references to MIPs across the codebase

echo "Finding MIP references..."
grep -h "MIP-[0-9]\+" *.md threat_model.md data_flows.md 2>/dev/null | grep -o "MIP-[0-9]\+" | sort | uniq
