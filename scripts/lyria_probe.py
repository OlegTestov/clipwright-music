import base64, json, os, sys, urllib.request
key = os.environ["GEMINI_API_KEY"]
model, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
req = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", data=json.dumps(body).encode(), headers={"content-type": "application/json", "x-goog-api-key": key})
try:
    j = json.load(urllib.request.urlopen(req, timeout=600))
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:600]); sys.exit(1)
parts = j["candidates"][0]["content"]["parts"]
for p in parts:
    if "inlineData" in p:
        open(out, "wb").write(base64.b64decode(p["inlineData"]["data"])); print("audio", p["inlineData"]["mimeType"], os.path.getsize(out))
    elif "text" in p:
        print("text:", p["text"][:300].replace("\n", " "))
print("usage", j.get("usageMetadata"))
