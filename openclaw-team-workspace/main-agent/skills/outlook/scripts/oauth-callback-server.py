#!/usr/bin/env python3
import sys
import urllib.parse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Outlook Authorization Successful</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --accent-color: #3b82f6;
            --accent-success: #10b981;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 1.5rem;
            box-sizing: border-box;
        }

        .container {
            background: var(--card-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 3rem 2.5rem;
            max-width: 500px;
            width: 100%;
            text-align: center;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2);
            animation: fadeIn 0.6s ease-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .icon-wrapper {
            width: 80px;
            height: 80px;
            background: rgba(16, 185, 129, 0.1);
            border: 2px solid var(--accent-success);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 2rem;
            box-shadow: 0 0 20px rgba(16, 185, 129, 0.2);
        }

        .icon {
            color: var(--accent-success);
            font-size: 2.5rem;
            font-weight: bold;
        }

        h1 {
            font-size: 1.8rem;
            font-weight: 600;
            margin: 0 0 1rem;
            letter-spacing: -0.02em;
        }

        p {
            font-size: 1.05rem;
            line-height: 1.6;
            color: var(--text-secondary);
            margin: 0 0 1.5rem;
        }

        .highlight-box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 1.25rem;
            margin: 1.5rem 0 2rem;
            text-align: left;
        }

        .highlight-box h2 {
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--accent-color);
            margin: 0 0 0.5rem;
            font-weight: 600;
        }

        .highlight-box ol {
            margin: 0;
            padding-left: 1.25rem;
            color: var(--text-primary);
            font-size: 0.95rem;
        }

        .highlight-box li {
            margin-bottom: 0.5rem;
            line-height: 1.4;
        }

        .highlight-box li:last-child {
            margin-bottom: 0;
        }

        .btn-copy {
            background: var(--accent-color);
            color: white;
            border: none;
            padding: 0.85rem 1.75rem;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 500;
            cursor: pointer;
            width: 100%;
            transition: all 0.2s ease;
            box-shadow: 0 4px 14px rgba(59, 130, 246, 0.4);
        }

        .btn-copy:hover {
            background: #2563eb;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.6);
        }

        .btn-copy:active {
            transform: translateY(0);
        }

        .btn-copy.success {
            background: var(--accent-success);
            box-shadow: 0 4px 14px rgba(16, 185, 129, 0.4);
        }

        .footer {
            margin-top: 2rem;
            font-size: 0.8rem;
            color: rgba(148, 163, 184, 0.5);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon-wrapper">
            <span class="icon">✓</span>
        </div>
        <h1>Outlook Connection Established</h1>
        <p>You have successfully logged in and authorized the Outlook integration with Baseer Burhan!</p>
        
        <div class="highlight-box">
            <h2>Next Steps</h2>
            <ol>
                <li>Click the button below to copy this page's URL.</li>
                <li>Go back to your Baseer Burhan Assistant.</li>
                <li>Paste the copied URL and send it to the Assistant.</li>
            </ol>
        </div>

        <button class="btn-copy" id="copyBtn">Copy Redirect URL</button>
        
        <div class="footer">
            Powered by Baseer Burhan
        </div>
    </div>

    <script>
        const copyBtn = document.getElementById('copyBtn');
        copyBtn.addEventListener('click', () => {
            const url = window.location.href;
            navigator.clipboard.writeText(url).then(() => {
                copyBtn.textContent = '✓ Copied to Clipboard!';
                copyBtn.classList.add('success');
                setTimeout(() => {
                    copyBtn.textContent = 'Copy Redirect URL';
                    copyBtn.classList.remove('success');
                }, 3000);
            }).catch(err => {
                alert('Could not copy automatically. Please copy the URL from the browser address bar.');
            });
        });
    </script>
</body>
</html>
"""
class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress logging to stdout/stderr to keep terminal output clean
        pass

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path == "/favicon.ico":
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_CONTENT.encode("utf-8"))
        
        # Check if the code query parameter is present
        query = parsed_path.query
        params = urllib.parse.parse_qs(query)
        if "code" in params:
            _, server_port = self.server.server_address
            port_suffix = "" if server_port == 80 else f":{server_port}"
            redirect_url = f"http://localhost{port_suffix}{self.path}"
            
            print(redirect_url)
            sys.stdout.flush()
            # Stop the server after handling the successful redirect
            sys.exit(0)

def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--write-html":
        Path(sys.argv[2]).write_text(HTML_CONTENT, encoding="utf-8")
        return

    # Default HTTP port keeps the OAuth redirect URI as plain http://localhost.
    port = 80
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
        
    # Correctly formatted binding tuple
    server = HTTPServer(("localhost", port), CallbackHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        sys.exit(1)

if __name__ == "__main__":
    main()
