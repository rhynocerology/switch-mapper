import os, json
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
DATA_DIR = '/data'
DATA_FILE = os.path.join(DATA_DIR, 'ports.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'settings.json')

HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Switch Mapper</title>
    <style>
        body { background: #0f172a; color: #f8fafc; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding: 20px; margin: 0; min-height: 100vh; }
        .panel { background: #1e293b; padding: 30px; border-radius: 12px; border: 1px solid #334155; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        
        /* Desktop: 8 columns */
        .grid { display: grid; grid-template-columns: repeat(8, 1fr); gap: 16px; justify-content: center; }
        .port-pair { display: flex; flex-direction: column; gap: 16px; }
        
        /* Tablet: 4 columns */
        @media (max-width: 1000px) {
            .grid { grid-template-columns: repeat(4, 1fr); gap: 32px 16px; }
        }
        
        /* Mobile: 2 columns (blocks of 4 ports) */
        @media (max-width: 550px) {
            .grid { grid-template-columns: repeat(2, 1fr); gap: 32px 16px; }
            .panel { padding: 20px; }
        }

        .port { background: #334155; border-radius: 8px; width: 100px; height: 110px; display: flex; flex-direction: column; align-items: center; padding: 10px; box-sizing: border-box; cursor: pointer; border: 1px solid #475569; }
        .port:hover { background: #475569; transform: scale(1.05); transition: 0.2s; }
        .socket { background: #000; width: 60px; height: 40px; border-radius: 4px; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 6px; margin-bottom: 12px; border: 1px solid #000; }
        .led { width: 40px; height: 6px; border-radius: 2px; background: #334155; }
        .led.active { background: #22c55e; box-shadow: 0 0 8px #22c55e; }
        .port-num { font-size: 11px; font-weight: bold; color: #94a3b8; }
        .port-name { font-size: 12px; font-weight: bold; margin-top: 4px; text-align: center; overflow: hidden; white-space: nowrap; width: 100%; }
        
        dialog { background: #1e293b; color: white; padding: 24px; border-radius: 8px; border: 1px solid #475569; width: 90%; max-width: 320px; }
        dialog::backdrop { background: rgba(0,0,0,0.7); }
        label { font-size: 11px; color: #94a3b8; font-weight: bold; display: block; margin-top: 12px; }
        input, select { width: 100%; padding: 10px; margin-top: 4px; background: #0f172a; color: white; border: 1px solid #475569; border-radius: 4px; box-sizing: border-box; }
        button { padding: 10px 16px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; color: white; margin-top: 20px; }
        .btn-cancel { background: #475569; }
        .btn-cancel:hover { background: #334155; }
        .btn-save { background: #2563eb; float: right; }
        .btn-save:hover { background: #1d4ed8; }
        
        .header-container { display: flex; align-items: center; gap: 12px; margin-bottom: 30px; margin-top: 20px; text-align: center; }
        h1 { margin: 0; letter-spacing: 1px; font-size: 24px; }
        .edit-btn { background: #334155; border: 1px solid #475569; padding: 0; width: 34px; height: 34px; border-radius: 50%; font-size: 16px; margin: 0; display: flex; align-items: center; justify-content: center; color: #94a3b8; transition: 0.2s; }
        .edit-btn:hover { background: #475569; color: white; }
    </style>
</head>
<body>
    <div class="header-container">
        <h1 id="switch-title">Loading...</h1>
        <button onclick="openTitleM()" class="edit-btn" title="Edit Switch Name">✎</button>
    </div>
    
    <div class="panel"><div id="grid" class="grid"></div></div>
    
    <dialog id="modal">
        <h2 style="margin-top:0; border-bottom:1px solid #475569; padding-bottom:10px;">Edit Port <span id="m-id" style="color:#60a5fa"></span></h2>
        <label>DEVICE NAME</label>
        <input type="text" id="m-name" placeholder="e.g. Unraid Server">
        <label>VLAN</label>
        <input type="text" id="m-vlan" placeholder="1">
        <label>STATUS</label>
        <select id="m-status">
            <option value="empty">Empty / Disconnected</option>
            <option value="connected">Connected</option>
        </select>
        <div style="margin-top: 5px;">
            <button onclick="document.getElementById('modal').close()" class="btn-cancel">Cancel</button>
            <button onclick="save()" class="btn-save">Save</button>
        </div>
    </dialog>

    <dialog id="titleModal">
        <h2 style="margin-top:0; border-bottom:1px solid #475569; padding-bottom:10px;">Edit Switch Name</h2>
        <label>SWITCH NAME</label>
        <input type="text" id="m-title" placeholder="e.g. Core Switch">
        <div style="margin-top: 5px;">
            <button onclick="document.getElementById('titleModal').close()" class="btn-cancel">Cancel</button>
            <button onclick="saveTitle()" class="btn-save">Save</button>
        </div>
    </dialog>

    <script>
        let current = null;
        let pData = {};
        
        async function loadTitle() {
            try {
                const res = await fetch('/api/settings');
                const data = await res.json();
                document.getElementById('switch-title').innerText = data.title;
                document.title = data.title;
            } catch(e) {
                document.getElementById('switch-title').innerText = "TP-Link TL-SG1016DE";
            }
        }

        async function load() {
            const res = await fetch('/api/ports');
            pData = await res.json();
            const grid = document.getElementById('grid');
            grid.innerHTML = '';
            
            // Loop through ports in pairs (1 & 2, 3 & 4, etc.)
            for(let i = 1; i <= 15; i += 2) {
                let pairHTML = '<div class="port-pair">';
                
                // Top Port (1, 3, 5...)
                const pTop = pData[i] || {name: '', status: 'empty'};
                const activeTop = pTop.status === 'connected' ? 'active' : '';
                pairHTML += `
                    <div onclick="openM(${i})" class="port">
                        <div class="socket"><div class="led ${activeTop}"></div></div>
                        <span class="port-num">PORT ${i}</span>
                        <span class="port-name">${pTop.name}</span>
                    </div>`;
                    
                // Bottom Port (2, 4, 6...)
                const pBot = pData[i+1] || {name: '', status: 'empty'};
                const activeBot = pBot.status === 'connected' ? 'active' : '';
                pairHTML += `
                    <div onclick="openM(${i+1})" class="port">
                        <div class="socket"><div class="led ${activeBot}"></div></div>
                        <span class="port-num">PORT ${i+1}</span>
                        <span class="port-name">${pBot.name}</span>
                    </div>`;
                    
                pairHTML += '</div>';
                grid.innerHTML += pairHTML;
            }
        }

        function openM(id) {
            current = id;
            const p = pData[id] || {name:'', vlan:'1', status:'empty'};
            document.getElementById('m-id').innerText = id;
            document.getElementById('m-name').value = p.name;
            document.getElementById('m-vlan').value = p.vlan;
            document.getElementById('m-status').value = p.status;
            document.getElementById('modal').showModal();
        }

        function openTitleM() {
            document.getElementById('m-title').value = document.getElementById('switch-title').innerText;
            document.getElementById('titleModal').showModal();
        }

        async function save() {
            await fetch('/api/ports/' + current, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: document.getElementById('m-name').value,
                    vlan: document.getElementById('m-vlan').value,
                    status: document.getElementById('m-status').value
                })
            });
            document.getElementById('modal').close();
            load();
        }

        async function saveTitle() {
            await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    title: document.getElementById('m-title').value
                })
            });
            document.getElementById('titleModal').close();
            loadTitle();
        }

        loadTitle();
        load();
    </script>
</body>
</html>"""

def check_dir():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

def get_data():
    check_dir()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: return json.load(f)
    return {str(i): {"name": "", "vlan": "1", "status": "empty"} for i in range(1, 17)}

def get_settings():
    check_dir()
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'r') as f: return json.load(f)
    return {"title": "TP-Link TL-SG1016DE"}

@app.route('/')
def index():
    resp = make_response(HTML)
    resp.headers['Content-Type'] = 'text/html; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

@app.route('/api/ports', methods=['GET'])
def api_get(): return jsonify(get_data())

@app.route('/api/ports/<id>', methods=['POST'])
def api_post(id):
    d = get_data()
    d[id] = request.json
    check_dir()
    with open(DATA_FILE, 'w') as f: json.dump(d, f)
    return jsonify({"success": True})
    
@app.route('/api/settings', methods=['GET'])
def api_get_settings(): return jsonify(get_settings())

@app.route('/api/settings', methods=['POST'])
def api_post_settings():
    check_dir()
    with open(SETTINGS_FILE, 'w') as f: json.dump(request.json, f)
    return jsonify({"success": True})

if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)
