import sys
import json

def main():
    # Loop reading JSON-lines from stdin and reply for each line.
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            data = {"raw": line}

        response = {"received": data, "ack": True}
        #print("response2")
        print(json.dumps(response), flush=True)

        # Allow the caller to request the child to exit
        if isinstance(data, dict) and data.get("cmd") == "exit":
            break

if __name__ == '__main__':
    main()