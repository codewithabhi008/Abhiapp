import os
import shutil
from datetime import datetime, timezone
from flask import Flask, render_template, jsonify, send_from_directory
from config import Config
from database import db, init_db
from models import User, Folder, FileRecord, ActivityLog
from routes import auth_bp, dashboard_bp, files_bp, folders_bp, settings_bp
from utils.helpers import format_file_size

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    init_db(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(folders_bp)
    app.register_blueprint(settings_bp)

    # Service Worker Route at Root Scope for PWA
    @app.route('/sw.js')
    def service_worker():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'sw.js', mimetype='application/javascript')

    @app.route('/manifest.json')
    def manifest():
        return send_from_directory(os.path.join(app.root_path, 'static'), 'manifest.json', mimetype='application/json')

    # Error Handlers
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({
            'success': False,
            'error': 'Uploaded file exceeds the maximum allowed limit (1 GB).'
        }), 413

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('base.html', not_found=True), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'An internal server error occurred.'
        }), 500

    # Ensure storage directories exist
    os.makedirs(app.config['USERS_STORAGE_DIR'], exist_ok=True)

    # Seed demo account and engineering files on first launch
    with app.app_context():
        seed_default_data()

    return app


def seed_default_data():
    """Seeds default user 'abhi' with realistic engineering vault structure and sample files."""
    try:
        demo_user = User.query.filter_by(username='abhi').first()
        if not demo_user:
            demo_user = User(username='abhi', email='abhi@codewithabhi.com')
            demo_user.set_password('AbhiApp@2026')
            demo_user.last_login = datetime.now(timezone.utc)
            db.session.add(demo_user)
            db.session.flush()

            eng = Folder(user_id=demo_user.id, folder_name='Engineering')
            db.session.add(eng)
            db.session.flush()

            acad = Folder(user_id=demo_user.id, folder_name='AutoCAD', parent_folder_id=eng.id)
            sw = Folder(user_id=demo_user.id, folder_name='SolidWorks', parent_folder_id=eng.id)
            pdf_f = Folder(user_id=demo_user.id, folder_name='PDF', parent_folder_id=eng.id)
            bom_f = Folder(user_id=demo_user.id, folder_name='BOM', parent_folder_id=eng.id)
            db.session.add_all([acad, sw, pdf_f, bom_f])
            db.session.flush()

            panel = Folder(user_id=demo_user.id, folder_name='Panel', parent_folder_id=acad.id)
            busbar = Folder(user_id=demo_user.id, folder_name='Busbar', parent_folder_id=acad.id)
            fab = Folder(user_id=demo_user.id, folder_name='Fabrication', parent_folder_id=acad.id)

            parts = Folder(user_id=demo_user.id, folder_name='Parts', parent_folder_id=sw.id)
            assy = Folder(user_id=demo_user.id, folder_name='Assembly', parent_folder_id=sw.id)
            draw = Folder(user_id=demo_user.id, folder_name='Drawing', parent_folder_id=sw.id)
            db.session.add_all([panel, busbar, fab, parts, assy, draw])
            db.session.flush()

            user_dir = os.path.join(Config.USERS_STORAGE_DIR, str(demo_user.id))
            os.makedirs(user_dir, exist_ok=True)

            sample_files_info = [
                {
                    'orig_name': 'Panel_GA_General_Arrangement_v2.dwg',
                    'ext': '.dwg',
                    'cat': 'AutoCAD Drawings',
                    'folder_id': panel.id,
                    'desc': '415V Main LT Control Panel General Arrangement and Front Elevation drawing with busbar clearance specifications.',
                    'tags': 'panel, ga, autocad, 415v, general-arrangement',
                    'fav': True,
                    'content': b'ACAD-DWG-HEADER-SAMPLE-DATA-PANEL-GA-V2' * 15000
                },
                {
                    'orig_name': 'Busbar_Current_Density_Calculation.xlsx',
                    'ext': '.xlsx',
                    'cat': 'Excel / BOQ / BOM',
                    'folder_id': busbar.id,
                    'desc': 'Copper & Aluminium busbar temperature rise, ampacity rating, and fault current calculation sheet.',
                    'tags': 'busbar, copper, calculation, ampacity, bom',
                    'fav': True,
                    'content': b'PK\x03\x04\x14\x00\x06\x00EXCEL_BOM_BUSBAR_DATA_SAMPLE' * 2000
                },
                {
                    'orig_name': 'Enclosure_Mounting_Bracket.sldprt',
                    'ext': '.sldprt',
                    'cat': 'SolidWorks Files',
                    'folder_id': parts.id,
                    'desc': 'Sheet metal 2.5mm cold rolled steel mounting bracket with M8 extruded clinch nuts.',
                    'tags': 'solidworks, bracket, sheetmetal, enclosure, 3d',
                    'fav': True,
                    'content': b'SOLIDWORKS-PART-MODEL-SAMPLE-DATA-ENCLOSURE-BRACKET' * 12000
                },
                {
                    'orig_name': 'Motor_Drive_Shaft_Assembly.sldasm',
                    'ext': '.sldasm',
                    'cat': 'SolidWorks Files',
                    'folder_id': assy.id,
                    'desc': 'Complete motor drive shaft assembly with tapered roller bearings and flexible coupling.',
                    'tags': 'solidworks, assembly, shaft, motor, 3d-cad',
                    'fav': False,
                    'content': b'SOLIDWORKS-ASSEMBLY-DATA-SAMPLE-MOTOR-SHAFT' * 14000
                },
                {
                    'orig_name': 'Technical_Specification_Switchgear_LT.pdf',
                    'ext': '.pdf',
                    'cat': 'PDF Documents',
                    'folder_id': pdf_f.id,
                    'desc': 'Approved vendor technical datasheet and electrical protection scheme specification.',
                    'tags': 'spec, switchgear, lt, electrical, standard',
                    'fav': True,
                    'content': b'%PDF-1.4\n1 0 obj\n<< /Title (AbhiApp Technical Specification) /Author (AbhiApp Vault) >>\nendobj\n2 0 obj\n<< /Type /Catalog /Pages 3 0 R >>\nendobj\n3 0 obj\n<< /Type /Pages /Kids [4 0 R] /Count 1 >>\nendobj\n4 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 6 0 R >> >> >>\nendobj\n5 0 obj\n<< /Length 120 >>\nstream\nBT\n/F1 18 Tf\n70 700 Td\n(AbhiApp Digital Vault - Technical Specification Sheet) Tj\n/F1 12 Tf\n0 -30 Td\n(Verified Project Document: 415V Switchgear & Busbar Standards) Tj\nET\nendstream\nendobj\n6 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 7\n0000000000 65535 f\n0000000010 00000 n\n0000000085 00000 n\n0000000135 00000 n\n0000000195 00000 n\n0000000310 00000 n\n0000000480 00000 n\ntrailer\n<< /Size 7 /Root 2 0 R >>\nstartxref\n550\n%%EOF'
                },
                {
                    'orig_name': 'automation_controller.py',
                    'ext': '.py',
                    'cat': 'Programming',
                    'folder_id': None,
                    'desc': 'PLC Modbus TCP/IP telemetry ingestion and real-time monitoring controller script.',
                    'tags': 'python, automation, plc, modbus, telemetry',
                    'fav': False,
                    'content': b'''# AbhiApp Vault - Automation Controller Script
import time
import json

class PanelTelemetryMonitor:
    def __init__(self, host: str = "192.168.1.100", port: int = 502):
        self.host = host
        self.port = port
        self.connected = False
        print(f"[INIT] Telemetry controller initialized for {host}:{port}")

    def read_busbar_temperatures(self):
        """Poll 3-phase busbar thermal sensors (R-Y-B phases)."""
        readings = {
            "R_Phase_Celsius": 48.5,
            "Y_Phase_Celsius": 49.2,
            "B_Phase_Celsius": 47.8,
            "Ambient_Celsius": 29.4,
            "Status": "NORMAL"
        }
        return readings

    def monitor_loop(self):
        print("[MONITOR] Starting real-time sensor polling cycle...")
        data = self.read_busbar_temperatures()
        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    monitor = PanelTelemetryMonitor()
    monitor.monitor_loop()
'''
                }
            ]

            for s in sample_files_info:
                cat_slug = s['cat'].lower().replace('/', '_').replace(' ', '_').strip('_')
                cat_dir = os.path.join(user_dir, cat_slug)
                os.makedirs(cat_dir, exist_ok=True)

                disk_name = f"sample_{s['orig_name']}"
                disk_path = os.path.join(cat_dir, disk_name)
                with open(disk_path, 'wb') as f:
                    f.write(s['content'])

                rel_path = os.path.relpath(disk_path, Config.BASE_DIR)
                size = os.path.getsize(disk_path)

                rec = FileRecord(
                    user_id=demo_user.id,
                    original_name=s['orig_name'],
                    stored_name=disk_name,
                    file_path=rel_path,
                    file_extension=s['ext'],
                    file_size=size,
                    category=s['cat'],
                    folder_id=s['folder_id'],
                    description=s['desc'],
                    tags=s['tags'],
                    is_favorite=s['fav'],
                    uploaded_at=datetime.now(timezone.utc)
                )
                db.session.add(rec)

            db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[SEED ERROR]: {e}")


app = create_app()

if __name__ == '__main__':
    print("=" * 60)
    print("  AbhiApp - Your Personal Digital Vault is running!")
    print("  URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
