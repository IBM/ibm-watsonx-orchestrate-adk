import json
import sys
from deepdiff import DeepDiff

def compare_json(file1, file2):
    try:
        with open(file1, 'r') as f1, open(file2, 'r') as f2:
            json1 = json.load(f1)
            json2 = json.load(f2)

        diff = DeepDiff(json1, json2, verbose_level=2)
        if diff:
            print("Differences found:")
            print(json.dumps(diff, indent=2))
        else:
            print("No differences found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python compare_json.py <file1.json> <file2.json>")
    else:
        compare_json(sys.argv[1], sys.argv[2])
        