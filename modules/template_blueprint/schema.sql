-- template_blueprint/schema.sql
-- [模組名稱] 實體結構定義 (符合 CGS v2.1 與五大基石規範)

CREATE TABLE IF NOT EXISTS [table_name] (
    record_id TEXT PRIMARY KEY,            -- 業務流水號或主鍵
    tax_id TEXT,                           -- 通用基石四: 8碼公司統一編號
    agency_oid TEXT NOT NULL,              -- 通用基石一: 主管機關 OID
    admin_code TEXT,                       -- 通用基石二: 6碼行政區碼
    record_name TEXT NOT NULL,             -- 名稱
    status TEXT DEFAULT 'ACTIVE',          -- 狀態
    updated_at TEXT NOT NULL,              -- 通用基石五: ISO-8601 時間戳
    attributes_json TEXT                   -- 彈性擴充屬性 (JSON)
);

CREATE INDEX IF NOT EXISTS idx_[table_name]_tax_id ON [table_name](tax_id);
CREATE INDEX IF NOT EXISTS idx_[table_name]_admin_code ON [table_name](admin_code);
