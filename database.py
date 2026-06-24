import os
import pandas as pd
from sqlalchemy import create_engine, text

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_engine():
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


def init_db():
    with get_engine().begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS deployments (
                id SERIAL PRIMARY KEY,
                service_name VARCHAR(200),
                vendor_image VARCHAR(500),
                environment VARCHAR(50),
                use_vendor_image BOOLEAN,
                pipeline_name VARCHAR(300),
                pipeline_id INT,
                run_id INT,
                build_state VARCHAR(100),
                build_result VARCHAR(100),
                build_url TEXT,
                release_id INT,
                release_name VARCHAR(200),
                release_status VARCHAR(100),
                release_url TEXT,
                release_environment_status TEXT,
                approval_status TEXT,
                error TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );
        """))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS release_id INT;"))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS release_name VARCHAR(200);"))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS release_status VARCHAR(100);"))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS release_url TEXT;"))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS release_environment_status TEXT;"))
        conn.execute(text("ALTER TABLE deployments ADD COLUMN IF NOT EXISTS approval_status TEXT;"))


def insert_deployment(run):
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO deployments (
                service_name, vendor_image, environment, use_vendor_image,
                pipeline_name, pipeline_id, run_id, build_state,
                build_result, build_url, error
            ) VALUES (
                :service_name, :vendor_image, :environment, :use_vendor_image,
                :pipeline_name, :pipeline_id, :run_id, :build_state,
                :build_result, :build_url, :error
            )
        """), {
            "service_name": run.get("Service"),
            "vendor_image": run.get("vendorImage"),
            "environment": run.get("Environment"),
            "use_vendor_image": run.get("useVendorImage"),
            "pipeline_name": run.get("Pipeline Name"),
            "pipeline_id": run.get("Pipeline ID") or None,
            "run_id": run.get("Run ID") or None,
            "build_state": run.get("State"),
            "build_result": run.get("Result"),
            "build_url": run.get("URL"),
            "error": run.get("Error"),
        })


def get_deployments_by_date(selected_date):
    return pd.read_sql(text("""
        SELECT id, service_name, vendor_image, environment, use_vendor_image,
               pipeline_name, pipeline_id, run_id, build_state, build_result,
               build_url, release_id, release_name, release_status, release_url,
               release_environment_status, approval_status, error, created_at, updated_at
        FROM deployments
        WHERE DATE(created_at) = :selected_date
        ORDER BY id DESC
    """), get_engine(), params={"selected_date": selected_date})


def update_build_status(row_id, state, result, url, error):
    with get_engine().begin() as conn:
        conn.execute(text("""
            UPDATE deployments
            SET build_state = :state,
                build_result = :result,
                build_url = :url,
                error = :error,
                updated_at = NOW()
            WHERE id = :id
        """), {"id": int(row_id), "state": state, "result": result, "url": url, "error": error})


def update_release_details(row_id, release):
    environments = release.get("environments", [])
    env_status = ", ".join([f"{env.get('name')}={env.get('status')}" for env in environments])
    with get_engine().begin() as conn:
        conn.execute(text("""
            UPDATE deployments
            SET release_id = :release_id,
                release_name = :release_name,
                release_status = :release_status,
                release_url = :release_url,
                release_environment_status = :release_environment_status,
                updated_at = NOW()
            WHERE id = :id
        """), {
            "id": int(row_id),
            "release_id": release.get("id"),
            "release_name": release.get("name"),
            "release_status": release.get("status"),
            "release_url": release.get("_links", {}).get("web", {}).get("href", ""),
            "release_environment_status": env_status,
        })
