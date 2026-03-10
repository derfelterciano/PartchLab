#!/usr/bin/env bash

while IFS= read -r package; do
    pkg=$(echo "$package" | sed 's/[=><!].*//')
    pip install "$pkg" || echo "Skipping $pkg"
done < requirements.txt
