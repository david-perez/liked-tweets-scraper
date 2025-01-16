#!/bin/bash

# Check if the input directory is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <directory_of_json_files>"
  exit 1
fi

input_dir="$1"

# Process each JSON file in the directory in ascending filename order, so that
# requests that we made first appear first in the output JSON array. That way
# tweets which we liked more recently will appear earlier in the array.
#
# This uses `sort` with two options:
#
#   -t'_' specifies the underscore (_) as the field delimiter.
#   -k2,2n sorts by the second field numerically, i.e., the part before the decimal point (e.g., 189514).
#   -k3,3n sorts numerically by the third field, which is the part after the decimal point (e.g., 302 in 189514.302).
#
for file in $(find "$input_dir" -type f -name "*.json" | sort -t'_' -k2,2n -k3,3n); do
  if [ -f "$file" ]; then
      jq -f transform.jq "$file" >> /tmp/process_jsons.tmp.json
  fi
done

jq -s '.' /tmp/process_jsons.tmp.json

rm /tmp/process_jsons.tmp.json
