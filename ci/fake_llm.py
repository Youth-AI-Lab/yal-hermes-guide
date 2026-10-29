"""Fake OpenAI-compatible endpoint: records each request body, and answers with the scripted
replies of script.json in order (tool calls, then a text), or with a fixed text.

Usage (started by check_hermes.py): python3 -I fake_llm.py <port> <requests folder> [script.json]
"""
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = int(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
COUNT = [0]
# Optional: a JSON list of scripted assistant replies, used in order for main chat requests (those with tools).
SCRIPT = json.loads(Path(sys.argv[3]).read_text()) if len(sys.argv) > 3 else []


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, stream=False):
        if stream:
            self.send_response(code)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for chunk in obj:
                self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/models"):
            self._send(200, {"object": "list", "data": [{"id": "fake-model", "object": "model",
                                                         "context_length": 200000}]})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        COUNT[0] += 1
        (OUT / f"{COUNT[0]:03d}-{self.path.strip('/').replace('/', '_')}.json").write_bytes(raw)
        try:
            req = json.loads(raw)
        except ValueError:
            req = {}
        text = "FAKE ANSWER"
        created = int(time.time())
        if SCRIPT and req.get("tools"):
            step = SCRIPT.pop(0)
            if "tool_calls" in step:
                calls = [{"id": f"call_{COUNT[0]}_{i}", "type": "function",
                          "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
                         for i, c in enumerate(step["tool_calls"])]
                msg = {"role": "assistant", "content": None, "tool_calls": calls}
                if req.get("stream"):
                    chunks = [{"id": "x", "object": "chat.completion.chunk", "created": created, "model": "fake-model",
                               "choices": [{"index": 0, "delta": {"role": "assistant", "tool_calls": [
                                   dict(c, index=i) for i, c in enumerate(calls)]}, "finish_reason": None}]},
                              {"id": "x", "object": "chat.completion.chunk", "created": created, "model": "fake-model",
                               "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
                               "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}]
                    self._send(200, chunks, stream=True)
                else:
                    self._send(200, {"id": "x", "object": "chat.completion", "created": created, "model": "fake-model",
                                     "choices": [{"index": 0, "message": msg, "finish_reason": "tool_calls"}],
                                     "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
                return
            text = step.get("text", text)
        if req.get("stream"):
            chunks = [
                {"id": "x", "object": "chat.completion.chunk", "created": created, "model": "fake-model",
                 "choices": [{"index": 0, "delta": {"role": "assistant", "content": text}, "finish_reason": None}]},
                {"id": "x", "object": "chat.completion.chunk", "created": created, "model": "fake-model",
                 "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                 "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
            ]
            self._send(200, chunks, stream=True)
        else:
            self._send(200, {"id": "x", "object": "chat.completion", "created": created, "model": "fake-model",
                             "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                                          "finish_reason": "stop"}],
                             "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})

    def log_message(self, *args):
        pass


HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
