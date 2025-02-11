#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Uses Semaphore's CLSClient to auto-classify a single document and sorts by topic score.

Outputs the classification results in JSON format.

Usage:
    semaphore-helper.py file_path
"""

import argparse
import subprocess
import re
import os
import json
from dotenv import load_dotenv

MAX_TOPICS = 10
SEMAPHORE_THRESHOLD = '48'
INCLUDE_SCORING = False

# Load configuration from environment variables
load_dotenv(override=True)
SEMAPHORE_JAVA_CLIENT = os.getenv('SEMAPHORE_JAVA_CLIENT')
SEMAPHORE_CLOUD_API_KEY = os.getenv('SEMAPHORE_CLOUD_API_KEY')
SEMAPHORE_URL = os.getenv('SEMAPHORE_URL')

if not all([SEMAPHORE_JAVA_CLIENT, SEMAPHORE_CLOUD_API_KEY, SEMAPHORE_URL]):
    raise ValueError(
        "Missing Semaphore environment variables. Ensure they are set before running the script.")


def parse_arguments():
    """Parse command-line arguments to get the file path."""
    parser = argparse.ArgumentParser(
        description="Process a single file with Semaphore's CLSClient"
    )
    parser.add_argument('file_path', help="Path to the file to process")
    return parser.parse_args()


def process_file(file_path):
    """Run Semaphore classification on a single file."""
    if not os.path.exists(file_path):
        print(json.dumps(
            {"error": f"File '{file_path}' does not exist."}, indent=4))
        return

    semantic_command = f'java -jar "{SEMAPHORE_JAVA_CLIENT}" --cloud-api-key={SEMAPHORE_CLOUD_API_KEY} --url={SEMAPHORE_URL} --threshold={SEMAPHORE_THRESHOLD} "{file_path}"'

    result = subprocess.run(
        semantic_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    if result.returncode == 0:
        # Process Semantic Classification result
        output_json = process_semantic_result(result.stdout)
        print(json.dumps(output_json, indent=4))
    else:
        print(json.dumps({"error": result.stderr}, indent=4))


def process_semantic_result(output):
    """Extract and sort classification results, outputting JSON."""
    start_str = '<SYSTEM name="Template" value="default"/>'
    end_str = '<ARTICLE>'

    result = re.search(
        f'{re.escape(start_str)}(.*?){re.escape(end_str)}', output, re.DOTALL
    )

    if not result:
        return {"topics": []}

    output = result.group(1).strip()

    pattern = r'<META name="Generic_UPWARD" value="(.*?)"[^>]*? score="(.*?)"'
    matches = re.findall(pattern, output)

    matches = sorted(set(matches), key=lambda x: float(x[1]), reverse=True)

    topics = [{"topic": value, "score": float(
        score)} for value, score in matches[:MAX_TOPICS]]

    return {"topics": topics}


def main():
    args = parse_arguments()
    process_file(args.file_path)


if __name__ == "__main__":
    main()
