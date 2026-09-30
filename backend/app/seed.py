from app.db import connect

def init_db():
    c = connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS boxes(id INTEGER PRIMARY KEY,name TEXT,length REAL,width REAL,height REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS papers(id INTEGER PRIMARY KEY,name TEXT,roll_width REAL,data_quality TEXT,note TEXT);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
    CREATE TABLE IF NOT EXISTS calc_runs(id INTEGER PRIMARY KEY AUTOINCREMENT,box_id INT,overlap REAL,result_json TEXT,note TEXT,created_at TEXT,voided TEXT NOT NULL DEFAULT 'active');
    CREATE TABLE IF NOT EXISTS cut_labels(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL,
      label_seq INTEGER NOT NULL,
      face_json TEXT NOT NULL,
      checksum TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','printed')),
      issued_at TEXT NOT NULL,
      printed_at TEXT,
      UNIQUE(run_id,label_seq),
      FOREIGN KEY(run_id) REFERENCES calc_runs(id)
    );
    CREATE INDEX IF NOT EXISTS idx_cut_labels_run ON cut_labels(run_id);
    """)
    # 迁移：旧库的 calc_runs 没有 voided 列
    cols = [r["name"] for r in c.execute("PRAGMA table_info(calc_runs)").fetchall()]
    if "voided" not in cols:
        c.execute("ALTER TABLE calc_runs ADD COLUMN voided TEXT NOT NULL DEFAULT 'active'")
    if c.execute("SELECT COUNT(*) c FROM boxes").fetchone()["c"] == 0:
        c.executemany("INSERT INTO boxes(name,length,width,height,data_quality,note) VALUES (?,?,?,?,?,?)",[
            ("书型盒",0.30,0.20,0.15,"clean",""),
            ("方形礼盒",0.25,0.25,0.10,"clean",""),
            ("脏数据-负高",0.2,0.2,-0.1,"dirty","高度负"),
        ])
        c.executemany("INSERT INTO papers(name,roll_width,data_quality,note) VALUES (?,?,?,?)",[
            ("哑光纸1.0m",1.0,"clean",""),
            ("牛皮纸0.7m",0.7,"clean",""),
        ])
        c.execute("INSERT INTO settings(key,value) VALUES ('overlap','1.15')")
        c.commit()
    c.close()
