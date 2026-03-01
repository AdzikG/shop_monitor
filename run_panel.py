"""
Uruchamia panel webowy WACEK - Strażnik TERGsasu.

Uzycie:
    python run_panel.py                # lokalnie port 8000
    python run_panel.py --port 8080    # inny port
    python run_panel.py --host 0.0.0.0 # dostep z sieci
"""

import uvicorn
import sys

if __name__ == "__main__":
    port = 8000
    host = "127.0.0.1"
    
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        port = int(sys.argv[idx + 1])
    
    if "--host" in sys.argv:
        idx = sys.argv.index("--host")
        host = sys.argv[idx + 1]
    
    print(f"Starting WACEK - Strażnik TERGsasu panel at http://{host}:{port}")
    print("Press Ctrl+C to stop")
    
    uvicorn.run("app.main:app", host=host, port=port, reload=False)
