import sqlite3
import os

def remove_cancelled_columns():
    """Remove is_cancelled related columns from all tables"""
    db_path = 'customer_supplier.db'
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table_name in tables:
            table_name = table_name[0]
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"Processing table: {table_name}")
            
            # Get table info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            # Check if table has cancellation columns
            has_cancelled_columns = any(col[1] in ['is_cancelled', 'cancelled_at', 'cancelled_by'] for col in columns)
            
            if has_cancelled_columns:
                print(f"  Found cancellation columns in {table_name}, removing...")
                
                # Create new table without cancellation columns
                new_columns = []
                for col in columns:
                    col_name = col[1]
                    if col_name not in ['is_cancelled', 'cancelled_at', 'cancelled_by']:
                        col_type = col[2]
                        col_notnull = "NOT NULL" if col[3] else ""
                        col_default = f"DEFAULT {col[4]}" if col[4] is not None else ""
                        col_pk = "PRIMARY KEY" if col[5] else ""
                        
                        col_def = f"{col_name} {col_type} {col_notnull} {col_default} {col_pk}".strip()
                        new_columns.append(col_def)
                
                # Create temporary table
                temp_table = f"{table_name}_temp"
                create_sql = f"CREATE TABLE {temp_table} ({', '.join(new_columns)})"
                cursor.execute(create_sql)
                
                # Copy data (excluding cancellation columns)
                select_columns = [col[1] for col in columns if col[1] not in ['is_cancelled', 'cancelled_at', 'cancelled_by']]
                copy_sql = f"INSERT INTO {temp_table} ({', '.join(select_columns)}) SELECT {', '.join(select_columns)} FROM {table_name}"
                cursor.execute(copy_sql)
                
                # Drop original table and rename temp table
                cursor.execute(f"DROP TABLE {table_name}")
                cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name}")
                
                print(f"  Successfully cleaned {table_name}")
            else:
                print(f"  No cancellation columns found in {table_name}")
        
        conn.commit()
        print("Database migration completed successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    remove_cancelled_columns()
