"""SQLite persistence, PBKDF2 passwords and hashed opaque sessions. No credentials seeded."""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
import uuid
from fastapi import HTTPException

DEMO_FARM = 'pp1_synthetic_demo'
ITERATIONS = 600_000


def password_hash(password):
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return f'pbkdf2_sha256${ITERATIONS}${salt}${value}'


def verify_password(password, saved):
    _, rounds, salt, expected = saved.split('$')
    actual = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), int(rounds)).hex()
    return hmac.compare_digest(actual, expected)


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token(token):
    return hmac.new(token.encode(), b'c2-local-session-csrf-v1', hashlib.sha256).hexdigest()


def default_path():
    return Path(os.environ.get('C2_ACCESS_DB', str(Path(os.environ.get('LOCALAPPDATA', Path.home()))/'SmartAgricultureC2'/'access.sqlite3'))).expanduser().resolve()


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','researcher','viewer')),active INTEGER NOT NULL DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessions(id_hash TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id),created REAL,seen REAL,expires REAL);
            CREATE TABLE IF NOT EXISTS attempts(client TEXT,username TEXT,created REAL);
            CREATE TABLE IF NOT EXISTS farms(farm_id TEXT PRIMARY KEY,farm_name TEXT,district TEXT,latitude REAL,longitude REAL,timezone TEXT,crop_type TEXT,growth_stage TEXT,is_demo INTEGER NOT NULL,provenance TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS memberships(user_id TEXT REFERENCES users(id),farm_id TEXT REFERENCES farms(farm_id),PRIMARY KEY(user_id,farm_id));
            CREATE TABLE IF NOT EXISTS farm_owners(farm_id TEXT PRIMARY KEY REFERENCES farms(farm_id),user_id TEXT NOT NULL REFERENCES users(id));
            CREATE TABLE IF NOT EXISTS sites(site_id TEXT PRIMARY KEY,farm_id TEXT REFERENCES farms(farm_id),site_name TEXT);
            CREATE TABLE IF NOT EXISTS nodes(node_id TEXT PRIMARY KEY,site_id TEXT REFERENCES sites(site_id),is_demo INTEGER NOT NULL,source TEXT,sensor_metadata TEXT,calibration_reference TEXT);
            CREATE TABLE IF NOT EXISTS forecasts(forecast_id TEXT PRIMARY KEY,farm_id TEXT REFERENCES farms(farm_id),site_id TEXT,node_id TEXT,created REAL,created_by TEXT REFERENCES users(id),model TEXT,history_sha256 TEXT,response TEXT);
            CREATE INDEX IF NOT EXISTS forecast_farm ON forecasts(farm_id,created);
            ''')
            db.execute('INSERT OR IGNORE INTO farms VALUES(?,?,?,?,?,?,?,?,?,?)',
                       (DEMO_FARM,'PP1 synthetic demonstration','Not verified',None,None,'Asia/Colombo','Capsicum chinense',None,1,'synthetic_2025_two_nodes'))
            for node in ('NODE_01','NODE_02'):
                site = 'demo_site_'+node.lower()
                db.execute('INSERT OR IGNORE INTO sites VALUES(?,?,?)',(site,DEMO_FARM,'Synthetic site '+node))
                db.execute('INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?)',(node,site,1,'synthetic_2025_two_nodes','Conceptual synthetic node; no registered hardware',None))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def bootstrap(self, username, password):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
                raise ValueError('Bootstrap is only permitted for an empty user database')
            user_id = uuid.uuid4().hex
            db.execute('INSERT INTO users VALUES(?,?,?,?,1)',(user_id,username.lower(),password_hash(password),'admin'))
            db.execute('INSERT INTO memberships VALUES(?,?)',(user_id,DEMO_FARM))
        return user_id

    def login(self, username, password, client):
        now = time.time(); username = username.lower()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE created<?',(now-900,))
            counts = db.execute('SELECT count(*),sum(username=?) FROM attempts WHERE client=?',(username,client)).fetchone()
            if counts[0] >= 20 or (counts[1] or 0) >= 5:
                raise HTTPException(429,'Too many login attempts; wait 15 minutes')
            db.execute('INSERT INTO attempts VALUES(?,?,?)',(client,username,now))
            user = db.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        # Equivalent KDF work for nonexistent users; no account-existence response.
        saved = user['password_hash'] if user else f'pbkdf2_sha256${ITERATIONS}$'+('00'*16)+'$'+('00'*32)
        if not verify_password(password,saved) or not user or not user['active']:
            raise HTTPException(401,'Invalid username or password')
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            fresh = db.execute('SELECT * FROM users WHERE id=? AND active=1',(user['id'],)).fetchone()
            if not fresh: raise HTTPException(401,'Invalid username or password')
            db.execute('DELETE FROM sessions WHERE expires<? OR seen<?',(now,now-1800))
            db.execute('INSERT INTO sessions VALUES(?,?,?,?,?)',(token_hash(token),user['id'],now,now,now+28800))
        return token

    def principal(self, token):
        if not token or len(token)>100: raise HTTPException(401,'Sign in required')
        now=time.time()
        with self.db() as db:
            row=db.execute('SELECT u.id,u.username,u.role FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.id_hash=? AND s.expires>? AND s.seen>? AND u.active=1',(token_hash(token),now,now-1800)).fetchone()
            if not row: raise HTTPException(401,'Session expired; sign in again')
            db.execute('UPDATE sessions SET seen=? WHERE id_hash=?',(now,token_hash(token)))
            return dict(row)

    def logout(self, token):
        with self.db() as db: db.execute('DELETE FROM sessions WHERE id_hash=?',(token_hash(token),))

    def session_remaining(self,token):
        with self.db() as db:
            row=db.execute('SELECT expires FROM sessions WHERE id_hash=?',(token_hash(token),)).fetchone()
            return max(0,int(row['expires']-time.time())) if row else 0

    def users(self):
        with self.db() as db: return [dict(r) for r in db.execute('SELECT id,username,role,active FROM users ORDER BY username')]

    def create_user(self, data):
        with self.db() as db:
            user_id=uuid.uuid4().hex
            try: db.execute('INSERT INTO users VALUES(?,?,?,?,1)',(user_id,data.username.lower(),password_hash(data.password.get_secret_value()),data.role))
            except sqlite3.IntegrityError as exc: raise HTTPException(409,'Username already exists') from exc
        return user_id

    def register(self, data, client):
        # Persist rejected attempts too; throttle before expensive password hashing.
        key='registration:'+client
        now=time.time()
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM attempts WHERE created<?',(now-900,))
            count=db.execute('SELECT count(*) FROM attempts WHERE client=?',(key,)).fetchone()[0]
            if count>=5: raise HTTPException(429,'Too many registration attempts; wait 15 minutes')
            db.execute('INSERT INTO attempts VALUES(?,?,?)',(key,data.username.lower(),now))
        from .schemas import NewUser
        return self.create_user(NewUser(username=data.username,password=data.password,role='viewer'))

    @staticmethod
    def farm_writer(db, user, farm_id):
        farm=Store.farm_access(db,user,farm_id)
        owner=db.execute('SELECT 1 FROM farm_owners WHERE farm_id=? AND user_id=?',(farm_id,user['id'])).fetchone()
        if user['role']!='admin' and (user['role']!='viewer' or not owner or farm['is_demo']):
            raise HTTPException(403,'Only the farm owner or an administrator may edit this farm')
        return farm

    def update_user(self, user_id, data):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone()
            if not old: raise HTTPException(404,'User not found')
            if old['role']=='admin' and old['active'] and (data.role!='admin' or not data.active):
                if db.execute("SELECT count(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]<=1:
                    raise HTTPException(409,'Cannot remove the last active administrator')
            db.execute('UPDATE users SET role=?,active=? WHERE id=?',(data.role,int(data.active),user_id))
            db.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))

    @staticmethod
    def farm_access(db, user, farm_id, member=False):
        row=db.execute('SELECT f.*,EXISTS(SELECT 1 FROM memberships m WHERE m.user_id=? AND m.farm_id=f.farm_id) AS assigned FROM farms f WHERE farm_id=?',(user['id'],farm_id)).fetchone()
        if not row or (not row['assigned'] and (member or user['role']!='admin')):
            raise HTTPException(404,'Farm not found')
        return dict(row)

    def farms(self, user):
        with self.db() as db:
            ids=[r[0] for r in db.execute('SELECT farm_id FROM farms ORDER BY farm_name')]
            result=[]
            for farm_id in ids:
                try: farm=self.farm_access(db,user,farm_id)
                except HTTPException: continue
                farm['owned']=bool(db.execute('SELECT 1 FROM farm_owners WHERE farm_id=? AND user_id=?',(farm_id,user['id'])).fetchone())
                farm['sites']=[]
                if user['role']=='admin':
                    farm['members']=[dict(row) for row in db.execute('SELECT u.id,u.username,u.role FROM memberships m JOIN users u ON u.id=m.user_id WHERE m.farm_id=? ORDER BY u.username',(farm_id,))]
                for row in db.execute('SELECT * FROM sites WHERE farm_id=? ORDER BY site_name',(farm_id,)):
                    site=dict(row);site['nodes']=[dict(n) for n in db.execute('SELECT * FROM nodes WHERE site_id=? ORDER BY node_id',(site['site_id'],))]
                    farm['sites'].append(site)
                result.append(farm)
            return result

    def write_farm(self, user, data, farm_id=None):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            existing=self.farm_writer(db,user,farm_id) if farm_id else None
            if not farm_id and user['role'] not in ('admin','viewer'):
                raise HTTPException(403,'Farm creation requires Farmer or Admin permission')
            if not farm_id and user['role']!='admin' and data.is_demo:
                raise HTTPException(403,'Only administrators may create sample farms')
            is_demo=bool(existing['is_demo']) if existing else data.is_demo
            if is_demo and (data.latitude is not None or data.longitude is not None or data.growth_stage is not None):
                raise HTTPException(422,'Demo locations and growth stage must remain unknown')
            values=data.model_dump(exclude={'is_demo'})
            provenance='synthetic_2025_two_nodes' if is_demo else 'operator_supplied_unverified; no observations ingested'
            if farm_id:
                db.execute('UPDATE farms SET farm_name=?,district=?,latitude=?,longitude=?,timezone=?,crop_type=?,growth_stage=?,provenance=? WHERE farm_id=?',(*values.values(),provenance,farm_id))
            else:
                farm_id=uuid.uuid4().hex
                db.execute('INSERT INTO farms VALUES(?,?,?,?,?,?,?,?,?,?)',(farm_id,*values.values(),int(is_demo),provenance))
                db.execute('INSERT INTO memberships VALUES(?,?)',(user['id'],farm_id))
                db.execute('INSERT INTO farm_owners VALUES(?,?)',(farm_id,user['id']))
            return farm_id

    def site(self, user, farm_id, name):
        with self.db() as db:
            self.farm_access(db,user,farm_id)
            site_id=uuid.uuid4().hex
            db.execute('INSERT INTO sites VALUES(?,?,?)',(site_id,farm_id,name))
            return site_id

    def membership(self, user, farm_id, user_id, granted):
        with self.db() as db:
            self.farm_access(db,user,farm_id)
            if not db.execute('SELECT 1 FROM users WHERE id=?',(user_id,)).fetchone(): raise HTTPException(404,'User not found')
            if granted: db.execute('INSERT OR IGNORE INTO memberships VALUES(?,?)',(user_id,farm_id))
            else: db.execute('DELETE FROM memberships WHERE user_id=? AND farm_id=?',(user_id,farm_id))

    def rename_site(self,user,farm_id,site_id,name):
        with self.db() as db:
            self.farm_access(db,user,farm_id)
            changed=db.execute('UPDATE sites SET site_name=? WHERE farm_id=? AND site_id=?',(name,farm_id,site_id))
            if changed.rowcount!=1:raise HTTPException(404,'Site not found in this farm')

    def register_node(self, data):
        with self.db() as db:
            try: db.execute('INSERT INTO nodes VALUES(?,NULL,0,?,?,?)',(data.node_id,'c1_not_ingested',data.sensor_metadata,data.calibration_reference))
            except sqlite3.IntegrityError as exc: raise HTTPException(409,'Node identifier already exists') from exc

    def assign_node(self, user, farm_id, site_id, node_id):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            farm=self.farm_access(db,user,farm_id)
            site=db.execute('SELECT 1 FROM sites WHERE site_id=? AND farm_id=?',(site_id,farm_id)).fetchone()
            node=db.execute('SELECT * FROM nodes WHERE node_id=?',(node_id,)).fetchone()
            if not site or not node: raise HTTPException(404,'Site or node not found')
            if bool(node['is_demo'])!=bool(farm['is_demo']): raise HTTPException(422,'Synthetic nodes must remain in demo farms; genuine-node registries cannot use demo sources')
            db.execute('UPDATE nodes SET site_id=? WHERE node_id=?',(site_id,node_id))

    def source(self, user, farm_id, site_id, node_id):
        with self.db() as db:
            farm=self.farm_access(db,user,farm_id,member=True)
            row=db.execute('SELECT n.* FROM nodes n JOIN sites s ON n.site_id=s.site_id WHERE n.node_id=? AND s.site_id=? AND s.farm_id=?',(node_id,site_id,farm_id)).fetchone()
            if not row: raise HTTPException(404,'Node does not belong to the selected farm/site')
            if not farm['is_demo'] or not row['is_demo'] or row['source']!='synthetic_2025_two_nodes':
                raise HTTPException(409,'Historical data unavailable: no verified 336-hour C1 history is ingested for this node')
            return dict(row)

    def save_forecast(self, user, farm_id, selection, request, response):
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT id,username,role FROM users WHERE id=? AND active=1',(user['id'],)).fetchone()
            if not current or current['role'] not in ('admin','researcher','viewer'): raise HTTPException(403,'Forecast permission revoked')
            user=dict(current)
            self.farm_access(db,user,farm_id,member=True)
            if not db.execute('SELECT 1 FROM nodes n JOIN sites s ON s.site_id=n.site_id WHERE n.node_id=? AND s.site_id=? AND s.farm_id=?',(selection.node_id,selection.site_id,farm_id)).fetchone():
                raise HTTPException(409,'Node assignment changed; select the site again')
            forecast_id=uuid.uuid4().hex
            fingerprint=hashlib.sha256(request.model_dump_json().encode()).hexdigest()
            db.execute('INSERT INTO forecasts VALUES(?,?,?,?,?,?,?,?,?)',(forecast_id,farm_id,selection.site_id,selection.node_id,time.time(),user['id'],selection.model,fingerprint,response.model_dump_json()))
            return forecast_id

    def forecasts(self, user, farm_id, site_id, node_id):
        with self.db() as db:
            self.farm_access(db,user,farm_id,member=True)
            if not db.execute('SELECT 1 FROM nodes n JOIN sites s ON s.site_id=n.site_id WHERE n.node_id=? AND s.site_id=? AND s.farm_id=?',(node_id,site_id,farm_id)).fetchone():
                raise HTTPException(404,'Node does not belong to the selected farm/site')
            rows=db.execute('SELECT forecast_id,created,model,history_sha256,response FROM forecasts WHERE farm_id=? AND site_id=? AND node_id=? ORDER BY created DESC LIMIT 20',(farm_id,site_id,node_id))
            return [{**dict(r),'response':json.loads(r['response'])} for r in rows]
